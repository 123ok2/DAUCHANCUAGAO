import express from "express";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

// Body parser for JSON payloads (up to 50MB for rich photo routes)
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Ensure persistent data directory exists
const DATA_DIR = path.join(process.cwd(), "data");
const SHARED_ROUTES_FILE = path.join(DATA_DIR, "shared_routes.json");

if (!fs.existsSync(DATA_DIR)) {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  } catch (err) {
    console.error("Failed to create data dir:", err);
  }
}

// In-memory cache for 0ms sub-millisecond access
const sharedRoutesCache = new Map<string, any>();
const sharedRoutesCodeMap = new Map<string, string>(); // code -> id

// Load existing shared routes from disk on server startup
function loadSharedRoutesFromDisk() {
  try {
    if (fs.existsSync(SHARED_ROUTES_FILE)) {
      const raw = fs.readFileSync(SHARED_ROUTES_FILE, "utf8");
      const list = JSON.parse(raw);
      if (Array.isArray(list)) {
        list.forEach((item) => {
          if (item && item.id && item.payload) {
            sharedRoutesCache.set(item.id, item.payload);
            if (item.code) {
              sharedRoutesCodeMap.set(item.code.toUpperCase(), item.id);
            }
          }
        });
      }
      console.log(`[Gạo Maps Server] Loaded ${sharedRoutesCache.size} shared routes from disk.`);
    }
  } catch (err) {
    console.warn("[Gạo Maps Server] Notice loading shared routes disk file:", err);
  }
}

// Persist shared routes to disk asynchronously
function persistSharedRoutesToDisk() {
  try {
    const list: Array<{ id: string; code?: string; payload: any; updatedAt: string }> = [];
    sharedRoutesCache.forEach((payload, id) => {
      // Find code if any
      let code = "";
      for (const [c, routeId] of sharedRoutesCodeMap.entries()) {
        if (routeId === id) {
          code = c;
          break;
        }
      }
      list.push({ id, code, payload, updatedAt: new Date().toISOString() });
    });
    // Keep max 2000 most recent shared routes
    if (list.length > 2000) {
      list.splice(0, list.length - 2000);
    }
    fs.writeFileSync(SHARED_ROUTES_FILE, JSON.stringify(list, null, 2), "utf8");
  } catch (err) {
    console.warn("[Gạo Maps Server] Error persisting shared routes to disk:", err);
  }
}

loadSharedRoutesFromDisk();

// Helper to generate clean 6-character trip code (e.g. GM-7429)
function generateTripCode(): string {
  const chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"; // No confusing 0/O, 1/I
  let result = "GM";
  for (let i = 0; i < 4; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// In-memory cache for high-speed routing acceleration (coords+mode -> route geometry)
const serverRouteCache = new Map<string, { data: any; timestamp: number }>();
const serverNearestCache = new Map<string, { data: any; timestamp: number }>();
const MAX_SERVER_CACHE_SIZE = 5000;

// Helper to race multiple OSRM routing mirrors concurrently with automatic nearest-road snapping (radiuses=unlimited)
async function raceOsrmMirrors(coordsString: string, mode: string = "driving") {
  const isMotorcycle = mode === "motorcycle";
  const numPoints = coordsString.split(";").length;
  const radiusesParam = Array(numPoints).fill("unlimited").join(";");
  const fallbackRadiusesParam = Array(numPoints).fill("10000").join(";");

  const endpoints = [
    // Unlimited snap radius to automatically reach nearest road for difficult locations
    `https://routing.openstreetmap.de/routed-car/route/v1/driving/${coordsString}?overview=full&geometries=geojson&steps=true&radiuses=${radiusesParam}`,
    `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson&steps=true&radiuses=${radiusesParam}`,
    `https://routing.openstreetmap.de/routed-car/route/v1/driving/${coordsString}?overview=full&geometries=geojson&steps=true&radiuses=${fallbackRadiusesParam}`,
    isMotorcycle 
      ? `https://routing.openstreetmap.de/routed-bike/route/v1/driving/${coordsString}?overview=full&geometries=geojson&steps=true&radiuses=${radiusesParam}`
      : `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson&steps=true`
  ];

  const fetchWithTimeout = async (url: string) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3800);
    try {
      const resp = await fetch(url, {
        signal: controller.signal,
        headers: {
          "Accept": "application/json",
          "User-Agent": "GaoMaps-FastRouter/1.0"
        }
      });
      clearTimeout(timer);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json: any = await resp.json();
      if (json && json.routes && json.routes.length > 0) {
        return json;
      }
      throw new Error("No route found in response");
    } catch (err) {
      clearTimeout(timer);
      throw err;
    }
  };

  // Fast concurrent race: return whichever mirror responds first with valid data!
  return await Promise.any(endpoints.map(ep => fetchWithTimeout(ep)));
}

// Find nearest road point for a single coordinate
async function fetchNearestRoadPoint(lng: number, lat: number, mode: string = "driving") {
  const cacheKey = `${mode}:${lng.toFixed(5)},${lat.toFixed(5)}`;
  const cached = serverNearestCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < 3600000) {
    return cached.data;
  }

  const endpoints = [
    `https://routing.openstreetmap.de/routed-car/nearest/v1/driving/${lng},${lat}?number=1`,
    `https://router.project-osrm.org/nearest/v1/driving/${lng},${lat}?number=1`
  ];

  const fetchWithTimeout = async (url: string) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2500);
    try {
      const resp = await fetch(url, {
        signal: controller.signal,
        headers: { "Accept": "application/json", "User-Agent": "GaoMaps-FastRouter/1.0" }
      });
      clearTimeout(timer);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json: any = await resp.json();
      if (json && json.waypoints && json.waypoints.length > 0) {
        const wp = json.waypoints[0];
        return {
          location: [wp.location[1], wp.location[0]], // [lat, lng]
          distanceMeters: wp.distance || 0,
          name: wp.name || "Đường gần nhất"
        };
      }
      throw new Error("No nearest road found");
    } catch (e) {
      clearTimeout(timer);
      throw e;
    }
  };

  try {
    const result = await Promise.any(endpoints.map(ep => fetchWithTimeout(ep)));
    if (serverNearestCache.size > MAX_SERVER_CACHE_SIZE) {
      const firstKey = serverNearestCache.keys().next().value;
      if (firstKey) serverNearestCache.delete(firstKey);
    }
    serverNearestCache.set(cacheKey, { data: result, timestamp: Date.now() });
    return result;
  } catch (err) {
    return null;
  }
}

// ==========================================
// API ROUTES FIRST
// ==========================================

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", time: new Date().toISOString() });
});

// Nearest Accessible Road Snapper
app.get("/api/routing/nearest", async (req, res) => {
  try {
    const lat = parseFloat(req.query.lat as string);
    const lng = parseFloat(req.query.lng as string);
    const mode = (req.query.mode as string || "driving").trim();

    if (isNaN(lat) || isNaN(lng)) {
      return res.status(400).json({ success: false, error: "Invalid lat/lng" });
    }

    const nearest = await fetchNearestRoadPoint(lng, lat, mode);
    if (nearest) {
      return res.json({ success: true, data: nearest });
    }
    return res.json({ success: true, data: { location: [lat, lng], distanceMeters: 0, name: "Vị trí gốc" } });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: err?.message || "Failed to find nearest road" });
  }
});

// High-Speed Real-Road Routing Proxy Endpoint (with pairwise leg & nearest road snap fallback)
app.get("/api/routing/route", async (req, res) => {
  try {
    const coords = (req.query.coords as string || "").trim();
    const mode = (req.query.mode as string || "driving").trim();

    if (!coords || !coords.includes(",")) {
      return res.status(400).json({ success: false, error: "Missing or invalid coordinates parameter" });
    }

    const cacheKey = `${mode}:${coords}`;
    const cached = serverRouteCache.get(cacheKey);
    if (cached && (Date.now() - cached.timestamp < 3600000)) { // 1 hour memory cache
      return res.json({ success: true, fromCache: true, data: cached.data });
    }

    // Try direct multi-point route first
    try {
      const routeData = await raceOsrmMirrors(coords, mode);
      
      // Save to memory cache
      if (serverRouteCache.size > MAX_SERVER_CACHE_SIZE) {
        const firstKey = serverRouteCache.keys().next().value;
        if (firstKey) serverRouteCache.delete(firstKey);
      }
      serverRouteCache.set(cacheKey, { data: routeData, timestamp: Date.now() });

      return res.json({ success: true, fromCache: false, data: routeData });
    } catch (routeErr) {
      // If direct routing failed, split into pairwise segments and route each pair in parallel
      const points = coords.split(";").map(p => {
        const [lng, lat] = p.split(",").map(Number);
        return { lng, lat };
      });

      if (points.length >= 2) {
        // Route each leg (Pi -> Pi+1) independently in parallel
        const legPromises = [];
        for (let i = 0; i < points.length - 1; i++) {
          const pA = points[i];
          const pB = points[i + 1];
          const pairString = `${pA.lng},${pA.lat};${pB.lng},${pB.lat}`;
          
          legPromises.push((async () => {
            // 1. Try direct pair
            try {
              const pairData = await raceOsrmMirrors(pairString, mode);
              if (pairData && pairData.routes && pairData.routes[0]) {
                return { success: true, route: pairData.routes[0], pA, pB };
              }
            } catch (e) {}

            // 2. Try nearest-road snapped pair
            try {
              const [snapA, snapB] = await Promise.all([
                fetchNearestRoadPoint(pA.lng, pA.lat, mode),
                fetchNearestRoadPoint(pB.lng, pB.lat, mode)
              ]);

              const sLngA = snapA?.location ? snapA.location[1] : pA.lng;
              const sLatA = snapA?.location ? snapA.location[0] : pA.lat;
              const sLngB = snapB?.location ? snapB.location[1] : pB.lng;
              const sLatB = snapB?.location ? snapB.location[0] : pB.lat;
              const snappedPairString = `${sLngA},${sLatA};${sLngB},${sLatB}`;

              const snapData = await raceOsrmMirrors(snappedPairString, mode);
              if (snapData && snapData.routes && snapData.routes[0]) {
                const r = snapData.routes[0];
                if (r.geometry && Array.isArray(r.geometry.coordinates)) {
                  r.geometry.coordinates.unshift([pA.lng, pA.lat]);
                  r.geometry.coordinates.push([pB.lng, pB.lat]);
                }
                return { success: true, route: r, pA, pB, isSnapped: true };
              }
            } catch (e) {}

            // 3. Mathematical fallback for this isolated segment
            const distM = Math.round(Math.hypot((pB.lng - pA.lng) * 111320 * Math.cos(pA.lat * Math.PI / 180), (pB.lat - pA.lat) * 110540) * 1.25);
            const durSec = Math.round(distM / (mode === "motorcycle" ? 10.5 : 15.0));
            return {
              success: false,
              pA,
              pB,
              route: {
                distance: distM,
                duration: durSec,
                geometry: {
                  type: "LineString",
                  coordinates: [[pA.lng, pA.lat], [pB.lng, pB.lat]]
                },
                legs: [{
                  distance: distM,
                  duration: durSec,
                  summary: `Chặng ${i + 1}`
                }]
              }
            };
          })());
        }

        const legResults = await Promise.all(legPromises);

        // Stitch all legs together
        let combinedCoords: [number, number][] = [];
        let combinedDistance = 0;
        let combinedDuration = 0;
        let combinedLegs: any[] = [];

        legResults.forEach((lr, idx) => {
          const r = lr.route;
          const coords = r?.geometry?.coordinates || [[lr.pA.lng, lr.pA.lat], [lr.pB.lng, lr.pB.lat]];
          if (idx === 0) {
            combinedCoords.push(...coords);
          } else {
            combinedCoords.push(...coords.slice(1));
          }
          combinedDistance += (r.distance || 0);
          combinedDuration += (r.duration || 0);
          if (Array.isArray(r.legs) && r.legs.length > 0) {
            combinedLegs.push(...r.legs);
          } else {
            combinedLegs.push({
              distance: r.distance || 0,
              duration: r.duration || 0,
              summary: `Chặng ${idx + 1}`
            });
          }
        });

        const stitchedData = {
          code: "Ok",
          routes: [{
            distance: combinedDistance,
            duration: combinedDuration,
            geometry: {
              type: "LineString",
              coordinates: combinedCoords
            },
            legs: combinedLegs,
            isPairwiseStitched: true
          }]
        };

        if (serverRouteCache.size > MAX_SERVER_CACHE_SIZE) {
          const firstKey = serverRouteCache.keys().next().value;
          if (firstKey) serverRouteCache.delete(firstKey);
        }
        serverRouteCache.set(cacheKey, { data: stitchedData, timestamp: Date.now() });

        return res.json({ success: true, fromCache: false, isPairwiseStitched: true, data: stitchedData });
      }
      throw routeErr;
    }
  } catch (err: any) {
    return res.status(502).json({ success: false, error: err?.message || "All routing mirrors failed or timed out" });
  }
});

// Save shared route
app.post("/api/share", (req, res) => {
  try {
    const { id, code: customCode, payload } = req.body;
    if (!payload) {
      return res.status(400).json({ success: false, error: "Missing payload" });
    }

    const routeId = id || `rt_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`;
    let tripCode = customCode ? customCode.toUpperCase().trim() : generateTripCode();

    // Store in memory
    sharedRoutesCache.set(routeId, payload);
    sharedRoutesCodeMap.set(tripCode, routeId);

    // Save to disk
    persistSharedRoutesToDisk();

    return res.json({
      success: true,
      id: routeId,
      code: tripCode,
      message: "Lộ trình đã được lưu trữ thành công trên máy chủ!"
    });
  } catch (err: any) {
    console.error("[API Share Save Error]:", err);
    return res.status(500).json({ success: false, error: err?.message || "Internal server error" });
  }
});

// Get shared route by ID
app.get("/api/share/:id", (req, res) => {
  try {
    const routeId = req.params.id;
    if (!routeId) {
      return res.status(400).json({ success: false, error: "Missing route ID" });
    }

    const payload = sharedRoutesCache.get(routeId);
    if (payload) {
      // Find associated code
      let code = "";
      for (const [c, id] of sharedRoutesCodeMap.entries()) {
        if (id === routeId) {
          code = c;
          break;
        }
      }
      return res.json({ success: true, id: routeId, code, payload });
    }

    // Check if ID is actually a trip code
    const mappedId = sharedRoutesCodeMap.get(routeId.toUpperCase().trim());
    if (mappedId) {
      const codePayload = sharedRoutesCache.get(mappedId);
      if (codePayload) {
        return res.json({ success: true, id: mappedId, code: routeId.toUpperCase().trim(), payload: codePayload });
      }
    }

    return res.status(404).json({ success: false, error: "Không tìm thấy lộ trình này trên hệ thống." });
  } catch (err: any) {
    console.error("[API Share Get Error]:", err);
    return res.status(500).json({ success: false, error: err?.message || "Internal server error" });
  }
});

// Get shared route by Trip Code (e.g. GM8921 or GM-8921)
app.get("/api/share/code/:code", (req, res) => {
  try {
    const rawCode = (req.params.code || "").toUpperCase().replace(/[^A-Z0-9]/g, "").trim();
    if (!rawCode) {
      return res.status(400).json({ success: false, error: "Mã lộ trình không hợp lệ" });
    }

    // Exact match or partial match
    let targetId = sharedRoutesCodeMap.get(rawCode);
    if (!targetId) {
      // Try finding by stripping prefixes or searching
      for (const [c, id] of sharedRoutesCodeMap.entries()) {
        const cleanC = c.replace(/[^A-Z0-9]/g, "");
        if (cleanC === rawCode || cleanC.endsWith(rawCode)) {
          targetId = id;
          break;
        }
      }
    }

    if (targetId) {
      const payload = sharedRoutesCache.get(targetId);
      if (payload) {
        return res.json({ success: true, id: targetId, code: rawCode, payload });
      }
    }

    return res.status(404).json({ success: false, error: `Không tìm thấy lộ trình với mã "${req.params.code}".` });
  } catch (err: any) {
    console.error("[API Share Code Error]:", err);
    return res.status(500).json({ success: false, error: err?.message || "Internal server error" });
  }
});

// ==========================================
// VITE OR STATIC FILE SERVING
// ==========================================
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Gạo Maps Server] Running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
});
