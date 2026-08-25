with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update toolbar HTML options
old_select_html = '''          <!-- Journey Mode (Roundtrip vs Outbound vs Return) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-emerald-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Chế độ mô phỏng hành trình (Điểm 1 là nơi xuất phát và về đích khi khứ hồi)">
            <i class="fa-solid fa-arrows-spin text-[11px] sm:text-xs text-emerald-400 shrink-0"></i>
            <select id="cinema-journey-select" onchange="changeCinemaJourneyMode(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-emerald-300 outline-none cursor-pointer">
              <option value="roundtrip" class="bg-slate-900 text-emerald-400" selected>🌟 Khứ hồi (Đi & Về đích điểm 1)</option>
              <option value="outbound" class="bg-slate-900 text-white">🏁 Chiều đi (1 ➔ N)</option>
              <option value="return" class="bg-slate-900 text-white">🔄 Chiều về (N ➔ 1)</option>
            </select>
          </div>'''

new_select_html = '''          <!-- Journey Mode (Roundtrip vs Outbound vs Return) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-emerald-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Chế độ mô phỏng hành trình (Lượt đi A➔B, Lượt về B➔A, hoặc Cả 2 lượt)">
            <i class="fa-solid fa-arrows-spin text-[11px] sm:text-xs text-emerald-400 shrink-0"></i>
            <select id="cinema-journey-select" onchange="changeCinemaJourneyMode(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-emerald-300 outline-none cursor-pointer">
              <option value="roundtrip" class="bg-slate-900 text-emerald-400" selected>🌟 Cả 2 lượt (A ➔ B ➔ A)</option>
              <option value="outbound" class="bg-slate-900 text-white">🏁 Lượt đi (A ➔ B)</option>
              <option value="return" class="bg-slate-900 text-white">🔄 Lượt về (B ➔ A)</option>
            </select>
          </div>'''

if old_select_html in html:
    html = html.replace(old_select_html, new_select_html, 1)
    print('Updated select HTML')
else:
    print('Could not find old_select_html')

# 2. Add getCinemaInterpolatedPosition helper and update updateCinemaRouteGeometryCache
old_cache_fn = '''    function updateCinemaRouteGeometryCache(pathCoords) {
      if (!pathCoords || pathCoords.length < 2) return;
      const c = cinemaRouteTelemetryCache;
      c.routeId = cinemaTargetRouteId;
      c.journeyMode = cinemaJourneyMode;
      c.pathLength = pathCoords.length;
      c.mercatorPointsByZoom.clear();

      let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
      const cumulative = [0];
      let totalMeters = 0;

      for (let i = 0; i < pathCoords.length; i++) {
        const pt = pathCoords[i];
        if (pt.lat < minLat) minLat = pt.lat;
        if (pt.lat > maxLat) maxLat = pt.lat;
        if (pt.lng < minLng) minLng = pt.lng;
        if (pt.lng > maxLng) maxLng = pt.lng;

        if (i > 0) {
          const prev = pathCoords[i - 1];
          const segDist = getHaversineDistance(prev.lat, prev.lng, pt.lat, pt.lng);
          totalMeters += segDist;
          cumulative.push(totalMeters);
        }
      }
      c.minLat = minLat;
      c.maxLat = maxLat;
      c.minLng = minLng;
      c.maxLng = maxLng;
      c.wholeCenterLat = (minLat + maxLat) / 2;
      c.wholeCenterLng = (minLng + maxLng) / 2;
      c.cumulativeMeters = cumulative;
      c.totalRoadMeters = totalMeters;
      c.totalRoadKm = parseFloat((totalMeters / 1000).toFixed(1));'''

new_cache_fn = '''    // Arc-length parameterization: strictly uniform speed across all curves, bends and highways
    function getCinemaInterpolatedPosition(pathCoords, progress) {
      if (!pathCoords || pathCoords.length === 0) return null;
      if (pathCoords.length === 1) {
        return {
          currentIdx: 0,
          nextIdx: 0,
          segmentT: 0,
          lat: pathCoords[0].lat,
          lng: pathCoords[0].lng,
          pt1: pathCoords[0],
          pt2: pathCoords[0],
          targetMeters: 0
        };
      }

      const c = cinemaRouteTelemetryCache;
      if (!c.cumulativeMeters || c.cumulativeMeters.length !== pathCoords.length) {
        updateCinemaRouteGeometryCache(pathCoords);
      }

      const totalDist = c.totalRoadMeters || 0;
      const clampedProgress = Math.max(0, Math.min(progress, 1.0));

      if (totalDist <= 0) {
        const totalPoints = pathCoords.length;
        const currentIdxFloat = clampedProgress * (totalPoints - 1);
        const currentIdx = Math.min(Math.floor(currentIdxFloat), totalPoints - 1);
        const nextIdx = Math.min(currentIdx + 1, totalPoints - 1);
        const segmentT = currentIdxFloat - currentIdx;
        const pt1 = pathCoords[currentIdx];
        const pt2 = pathCoords[nextIdx];
        return {
          currentIdx,
          nextIdx,
          segmentT,
          lat: pt1.lat + (pt2.lat - pt1.lat) * segmentT,
          lng: pt1.lng + (pt2.lng - pt1.lng) * segmentT,
          pt1,
          pt2,
          targetMeters: 0
        };
      }

      const targetMeters = clampedProgress * totalDist;
      const cum = c.cumulativeMeters;

      // Binary search for ultra-fast O(log N) position lookup
      let low = 0;
      let high = cum.length - 1;
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        if (cum[mid] <= targetMeters) {
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }

      const currentIdx = Math.max(0, Math.min(high, pathCoords.length - 2));
      const nextIdx = Math.min(currentIdx + 1, pathCoords.length - 1);

      const d1 = cum[currentIdx];
      const d2 = cum[nextIdx];
      const segSpan = Math.max(0.0001, d2 - d1);
      const segmentT = Math.max(0, Math.min((targetMeters - d1) / segSpan, 1.0));

      const pt1 = pathCoords[currentIdx];
      const pt2 = pathCoords[nextIdx];
      const carLat = pt1.lat + (pt2.lat - pt1.lat) * segmentT;
      const carLng = pt1.lng + (pt2.lng - pt1.lng) * segmentT;

      return {
        currentIdx,
        nextIdx,
        segmentT,
        lat: carLat,
        lng: carLng,
        pt1,
        pt2,
        targetMeters
      };
    }

    function updateCinemaRouteGeometryCache(pathCoords) {
      if (!pathCoords || pathCoords.length < 2) return;
      const c = cinemaRouteTelemetryCache;
      c.routeId = cinemaTargetRouteId;
      c.journeyMode = cinemaJourneyMode;
      c.pathLength = pathCoords.length;
      c.mercatorPointsByZoom.clear();

      let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
      const cumulative = [0];
      let totalMeters = 0;

      for (let i = 0; i < pathCoords.length; i++) {
        const pt = pathCoords[i];
        if (pt.lat < minLat) minLat = pt.lat;
        if (pt.lat > maxLat) maxLat = pt.lat;
        if (pt.lng < minLng) minLng = pt.lng;
        if (pt.lng > maxLng) maxLng = pt.lng;

        if (i > 0) {
          const prev = pathCoords[i - 1];
          const segDist = getHaversineDistance(prev.lat, prev.lng, pt.lat, pt.lng);
          totalMeters += segDist;
          cumulative.push(totalMeters);
        }
      }
      c.minLat = minLat;
      c.maxLat = maxLat;
      c.minLng = minLng;
      c.maxLng = maxLng;
      c.wholeCenterLat = (minLat + maxLat) / 2;
      c.wholeCenterLng = (minLng + maxLng) / 2;
      c.cumulativeMeters = cumulative;
      c.totalRoadMeters = totalMeters;
      c.totalRoadKm = parseFloat((totalMeters / 1000).toFixed(1));'''

if old_cache_fn in html:
    html = html.replace(old_cache_fn, new_cache_fn, 1)
    print('Updated updateCinemaRouteGeometryCache and added getCinemaInterpolatedPosition')
else:
    print('Could not find old_cache_fn')

# 3. Update getDynamicCinemaViewport to use arc-length parametrization and distance-based lookahead
old_vp = '''    function getDynamicCinemaViewport(pathCoords, progress, canvasW, canvasH) {
      if (!pathCoords || pathCoords.length < 2) return null;

      const c = cinemaRouteTelemetryCache;
      if (c.pathLength !== pathCoords.length || c.routeId !== cinemaTargetRouteId || c.journeyMode !== cinemaJourneyMode) {
        updateCinemaRouteGeometryCache(pathCoords);
      }

      const wholeCenterLat = c.wholeCenterLat;
      const wholeCenterLng = c.wholeCenterLng;

      // Find current vehicle coordinates along path with sub-pixel interpolation
      const totalPoints = pathCoords.length;
      const currentIdxFloat = Math.max(0, Math.min(progress, 1.0)) * (totalPoints - 1);
      const currentIdx = Math.floor(currentIdxFloat);
      const nextIdx = Math.min(currentIdx + 1, totalPoints - 1);
      const segmentT = currentIdxFloat - currentIdx;

      const pt1 = pathCoords[currentIdx];
      const pt2 = pathCoords[nextIdx];
      const carLat = pt1.lat + (pt2.lat - pt1.lat) * segmentT;
      const carLng = pt1.lng + (pt2.lng - pt1.lng) * segmentT;

      const currentZoom = getEffectiveCinemaZoom(pathCoords, canvasW, canvasH);

      let camCenterLat = carLat;
      let camCenterLng = carLng;

      if (cinemaCameraMode === 'overview') {
        camCenterLat = wholeCenterLat;
        camCenterLng = wholeCenterLng;
      } else if (cinemaCameraMode === 'cinematic') {
        if (progress < 0.06) {
          const easeT = progress / 0.06;
          const smoothEase = easeT * easeT * (3 - 2 * easeT);
          camCenterLat = wholeCenterLat + (carLat - wholeCenterLat) * smoothEase;
          camCenterLng = wholeCenterLng + (carLng - wholeCenterLng) * smoothEase;
        } else if (progress > 0.94) {
          const easeT = (progress - 0.94) / 0.06;
          const smoothEase = easeT * easeT * (3 - 2 * easeT);
          camCenterLat = carLat + (wholeCenterLat - carLat) * smoothEase;
          camCenterLng = carLng + (wholeCenterLng - carLng) * smoothEase;
        } else {
          camCenterLat = carLat;
          camCenterLng = carLng;
        }
      } else {
        camCenterLat = carLat;
        camCenterLng = carLng;
      }

      const centerWorld = latLngToMercatorWorld(camCenterLat, camCenterLng, currentZoom);
      const carWorld = latLngToMercatorWorld(carLat, carLng, currentZoom);

      // Compute smoothed vehicle heading vector with lookahead tangent window
      const lookaheadIdx = Math.min(currentIdx + Math.max(2, Math.floor(totalPoints / 80)), totalPoints - 1);
      const lookPt = pathCoords[lookaheadIdx];
      const wLook = latLngToMercatorWorld(lookPt.lat, lookPt.lng, currentZoom);
      let targetHeading = 0;
      if (Math.hypot(wLook.x - carWorld.x, wLook.y - carWorld.y) > 0.1) {
        targetHeading = Math.atan2(wLook.y - carWorld.y, wLook.x - carWorld.x);
      } else {
        const w1 = latLngToMercatorWorld(pt1.lat, pt1.lng, currentZoom);
        const w2 = latLngToMercatorWorld(pt2.lat, pt2.lng, currentZoom);
        if (Math.hypot(w2.x - w1.x, w2.y - w1.y) > 0.1) {
          targetHeading = Math.atan2(w2.y - w1.y, w2.x - w1.x);
        }
      }

      if (cinemaSmoothedHeading === null) {
        cinemaSmoothedHeading = targetHeading;
      } else {
        let diff = targetHeading - cinemaSmoothedHeading;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        cinemaSmoothedHeading += diff * 0.18; // Smooth rotational lerp
      }'''

new_vp = '''    function getDynamicCinemaViewport(pathCoords, progress, canvasW, canvasH) {
      if (!pathCoords || pathCoords.length < 2) return null;

      const c = cinemaRouteTelemetryCache;
      if (c.pathLength !== pathCoords.length || c.routeId !== cinemaTargetRouteId || c.journeyMode !== cinemaJourneyMode) {
        updateCinemaRouteGeometryCache(pathCoords);
      }

      const wholeCenterLat = c.wholeCenterLat;
      const wholeCenterLng = c.wholeCenterLng;

      // Uniform speed vehicle position lookup (Arc-length Parameterized)
      const interp = getCinemaInterpolatedPosition(pathCoords, progress);
      if (!interp) return null;

      const carLat = interp.lat;
      const carLng = interp.lng;

      const currentZoom = getEffectiveCinemaZoom(pathCoords, canvasW, canvasH);

      let camCenterLat = carLat;
      let camCenterLng = carLng;

      if (cinemaCameraMode === 'overview') {
        camCenterLat = wholeCenterLat;
        camCenterLng = wholeCenterLng;
      } else if (cinemaCameraMode === 'cinematic') {
        if (progress < 0.06) {
          const easeT = progress / 0.06;
          const smoothEase = easeT * easeT * (3 - 2 * easeT);
          camCenterLat = wholeCenterLat + (carLat - wholeCenterLat) * smoothEase;
          camCenterLng = wholeCenterLng + (carLng - wholeCenterLng) * smoothEase;
        } else if (progress > 0.94) {
          const easeT = (progress - 0.94) / 0.06;
          const smoothEase = easeT * easeT * (3 - 2 * easeT);
          camCenterLat = carLat + (wholeCenterLat - carLat) * smoothEase;
          camCenterLng = carLng + (wholeCenterLng - carLng) * smoothEase;
        } else {
          camCenterLat = carLat;
          camCenterLng = carLng;
        }
      } else {
        camCenterLat = carLat;
        camCenterLng = carLng;
      }

      const centerWorld = latLngToMercatorWorld(camCenterLat, camCenterLng, currentZoom);
      const carWorld = latLngToMercatorWorld(carLat, carLng, currentZoom);

      // Smooth vehicle heading calculation using distance-based lookahead window (30m - 120m)
      // Guarantees stable orientation through sharp hairpins, roundabouts and straightaways
      const totalDist = c.totalRoadMeters || 0;
      const targetMeters = interp.targetMeters || (progress * totalDist);
      const lookaheadMeters = Math.min(totalDist, targetMeters + Math.max(30, Math.min(120, totalDist * 0.02)));
      const lookProg = totalDist > 0 ? (lookaheadMeters / totalDist) : Math.min(1.0, progress + 0.02);
      const lookInterp = getCinemaInterpolatedPosition(pathCoords, lookProg);

      let targetHeading = 0;
      if (lookInterp) {
        const wLook = latLngToMercatorWorld(lookInterp.lat, lookInterp.lng, currentZoom);
        if (Math.hypot(wLook.x - carWorld.x, wLook.y - carWorld.y) > 0.05) {
          targetHeading = Math.atan2(wLook.y - carWorld.y, wLook.x - carWorld.x);
        } else if (interp.pt1 && interp.pt2) {
          const w1 = latLngToMercatorWorld(interp.pt1.lat, interp.pt1.lng, currentZoom);
          const w2 = latLngToMercatorWorld(interp.pt2.lat, interp.pt2.lng, currentZoom);
          if (Math.hypot(w2.x - w1.x, w2.y - w1.y) > 0.05) {
            targetHeading = Math.atan2(w2.y - w1.y, w2.x - w1.x);
          }
        }
      }

      if (cinemaSmoothedHeading === null) {
        cinemaSmoothedHeading = targetHeading;
      } else {
        let diff = targetHeading - cinemaSmoothedHeading;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        cinemaSmoothedHeading += diff * 0.20; // Smooth rotational lerp
      }'''

if old_vp in html:
    html = html.replace(old_vp, new_vp, 1)
    print('Updated getDynamicCinemaViewport')
else:
    print('Could not find old_vp')

# 4. Update drawCinemaFrame traversed route & vehicle screen position
old_draw_traversed = '''      // Active traversed glowing route
      const currentIdxFloat = Math.max(0, Math.min(progress, 1.0)) * (numPts - 1);
      const currentIdx = Math.floor(currentIdxFloat);
      const nextIdx = Math.min(currentIdx + 1, numPts - 1);
      const segmentT = currentIdxFloat - currentIdx;

      const pCur = worldRoutePoints[currentIdx];
      const pNxt = worldRoutePoints[nextIdx];
      const curCarWorldX = pCur.x + (pNxt.x - pCur.x) * segmentT;
      const curCarWorldY = pCur.y + (pNxt.y - pCur.y) * segmentT;

      // Glow line
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.65)';
      ctx.lineWidth = 10 * uiScale;
      for (let i = 0; i <= currentIdx; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.lineTo(curCarWorldX, curCarWorldY);
      ctx.stroke();

      // Sharp bright neon trail
      ctx.beginPath();
      ctx.strokeStyle = '#0ea5e9';
      ctx.lineWidth = 4.5 * uiScale;
      for (let i = 0; i <= currentIdx; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.lineTo(curCarWorldX, curCarWorldY);
      ctx.stroke();'''

new_draw_traversed = '''      // Active traversed glowing route (strictly synchronized to uniform speed)
      const interp = getCinemaInterpolatedPosition(pathCoords, progress);
      const currentIdx = interp ? interp.currentIdx : 0;
      const nextIdx = interp ? interp.nextIdx : 0;
      const segmentT = interp ? interp.segmentT : 0;

      const pCur = worldRoutePoints[currentIdx] || worldRoutePoints[0];
      const pNxt = worldRoutePoints[nextIdx] || pCur;
      const curCarWorldX = pCur.x + (pNxt.x - pCur.x) * segmentT;
      const curCarWorldY = pCur.y + (pNxt.y - pCur.y) * segmentT;

      // Glow line
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.65)';
      ctx.lineWidth = 10 * uiScale;
      for (let i = 0; i <= currentIdx; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.lineTo(curCarWorldX, curCarWorldY);
      ctx.stroke();

      // Sharp bright neon trail
      ctx.beginPath();
      ctx.strokeStyle = '#0ea5e9';
      ctx.lineWidth = 4.5 * uiScale;
      for (let i = 0; i <= currentIdx; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.lineTo(curCarWorldX, curCarWorldY);
      ctx.stroke();'''

if old_draw_traversed in html:
    html = html.replace(old_draw_traversed, new_draw_traversed, 1)
    print('Updated drawCinemaFrame traversed polyline')
else:
    print('Could not find old_draw_traversed')

# 5. Update changeCinemaJourneyMode toast messages
old_change_j = '''      const modeNames = {
        roundtrip: '🌟 Khứ hồi (1 ➔ N ➔ 1)',
        outbound: '🏁 Chiều đi (1 ➔ N)',
        return: '🔄 Chiều về (N ➔ 1)'
      };
      showToast(`Đã chọn chế độ quay/mô phỏng: ${modeNames[cinemaJourneyMode] || mode}`, 'success');'''

new_change_j = '''      const modeNames = {
        roundtrip: '🌟 Cả 2 lượt (A ➔ B ➔ A) • Tốc độ đều êm ái',
        outbound: '🏁 Lượt đi (A ➔ B) • Tốc độ đều êm ái',
        return: '🔄 Lượt về (B ➔ A) • Tốc độ đều êm ái'
      };
      showToast(`Đã chọn hành trình: ${modeNames[cinemaJourneyMode] || mode}`, 'success');'''

if old_change_j in html:
    html = html.replace(old_change_j, new_change_j, 1)
    print('Updated changeCinemaJourneyMode toast')
else:
    print('Could not find old_change_j')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('All smooth journey speed updates applied!')
