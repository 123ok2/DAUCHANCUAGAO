import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

draw_func_code = '''    function drawCinemaFrame(progress, pathCoords) {
      const canvas = document.getElementById('cinema-canvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;

      // Enable High Quality Anti-Aliasing
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = cinemaQuality === '1080p' ? 'high' : 'medium';

      const vp = getDynamicCinemaViewport(pathCoords, progress, w, h);
      if (!vp) return;

      const c = cinemaRouteTelemetryCache;
      const uiScale = w / 1080; // Scale UI graphics proportionally
      const isPortrait = h > w;

      // Determine 3D Perspective Tilt Parameters (Steady Camera - North-Up)
      const isTilt = cinemaTiltAngle > 0 && cinemaCameraMode !== 'overview';
      const tiltRad = (cinemaTiltAngle * Math.PI) / 180;
      const pitchScaleY = isTilt ? Math.cos(tiltRad) : 1.0;
      const anchorScreenX = w / 2;
      const anchorScreenY = isTilt ? (h * 0.58) : (h / 2);

      // Function to transform world point to screen coordinates
      function worldToScreen(wx, wy) {
        if (!isTilt) {
          return {
            x: (w / 2) + (wx - vp.centerWorldX),
            y: (h / 2) + (wy - vp.centerWorldY)
          };
        }
        const dx = wx - vp.carWorldX;
        const dy = wy - vp.carWorldY;
        return {
          x: anchorScreenX + dx,
          y: anchorScreenY + dy * pitchScaleY
        };
      }

      // 1. Clear background
      ctx.fillStyle = cinemaMapStyle === 'dark' ? '#090d16' : (cinemaMapStyle === 'satellite' ? '#050c1c' : '#cbd5e1');
      ctx.fillRect(0, 0, w, h);

      // 2. Render Map Tiles
      ctx.save();
      if (isTilt) {
        ctx.translate(anchorScreenX, anchorScreenY);
        ctx.scale(1, pitchScaleY);
        ctx.translate(-vp.carWorldX, -vp.carWorldY);
      } else {
        ctx.translate((w / 2) - vp.centerWorldX, (h / 2) - vp.centerWorldY);
      }

      if (cinemaMapStyle === 'grid') {
        ctx.fillStyle = '#090d16';
        ctx.fillRect(vp.minTx * 256, vp.minTy * 256, (vp.maxTx - vp.minTx + 1) * 256, (vp.maxTy - vp.minTy + 1) * 256);
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 1.5 * uiScale;
        const startX = vp.minTx * 256;
        const endX = (vp.maxTx + 1) * 256;
        const startY = vp.minTy * 256;
        const endY = (vp.maxTy + 1) * 256;
        for (let x = startX; x <= endX; x += 50) {
          ctx.beginPath(); ctx.moveTo(x, startY); ctx.lineTo(x, endY); ctx.stroke();
        }
        for (let y = startY; y <= endY; y += 50) {
          ctx.beginPath(); ctx.moveTo(startX, y); ctx.lineTo(endX, y); ctx.stroke();
        }
      } else {
        for (let tx = vp.minTx; tx <= vp.maxTx; tx++) {
          for (let ty = vp.minTy; ty <= vp.maxTy; ty++) {
            const img = getOrCreateTileImage(cinemaMapStyle, vp.zoom, tx, ty);
            if (img && img.complete && img.naturalWidth > 0) {
              ctx.drawImage(img, tx * 256, ty * 256, 256, 256);
            }
          }
        }
      }

      // 3. Draw Road Polyline in Map Space (Fast cached Mercator points)
      let worldRoutePoints = c.mercatorPointsByZoom.get(vp.zoom);
      if (!worldRoutePoints) {
        worldRoutePoints = pathCoords.map(pt => latLngToMercatorWorld(pt.lat, pt.lng, vp.zoom));
        c.mercatorPointsByZoom.set(vp.zoom, worldRoutePoints);
      }

      // Inactive track (dark outline)
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.lineWidth = 9 * uiScale;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      const numPts = worldRoutePoints.length;
      for (let i = 0; i < numPts; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.stroke();

      ctx.beginPath();
      ctx.strokeStyle = cinemaMapStyle === 'dark' ? '#334155' : '#64748b';
      ctx.lineWidth = 4.5 * uiScale;
      for (let i = 0; i < numPts; i++) {
        const pt = worldRoutePoints[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.stroke();

      // Active traversed glowing route (strictly synchronized to uniform speed)
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
      ctx.stroke();

      ctx.restore(); // Exit 3D map tile coordinate space

      // 4. Atmospheric Horizon Sky Effect (For 3D Tilt View)
      if (isTilt) {
        const horizonH = 160 * uiScale;
        const horizonGrad = ctx.createLinearGradient(0, 0, 0, horizonH);
        if (cinemaMapStyle === 'satellite') {
          horizonGrad.addColorStop(0, 'rgba(5, 12, 28, 0.96)');
          horizonGrad.addColorStop(0.5, 'rgba(14, 165, 233, 0.3)');
          horizonGrad.addColorStop(1, 'rgba(5, 12, 28, 0)');
        } else if (cinemaMapStyle === 'dark') {
          horizonGrad.addColorStop(0, 'rgba(9, 13, 22, 0.98)');
          horizonGrad.addColorStop(0.5, 'rgba(99, 102, 241, 0.25)');
          horizonGrad.addColorStop(1, 'rgba(9, 13, 22, 0)');
        } else {
          horizonGrad.addColorStop(0, 'rgba(203, 213, 225, 0.95)');
          horizonGrad.addColorStop(0.5, 'rgba(226, 232, 240, 0.4)');
          horizonGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        }
        ctx.fillStyle = horizonGrad;
        ctx.fillRect(0, 0, w, horizonH);

        // Subtle horizon line accent
        ctx.beginPath();
        ctx.moveTo(0, 8 * uiScale);
        ctx.lineTo(w, 8 * uiScale);
        ctx.strokeStyle = cinemaMapStyle === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 1 * uiScale;
        ctx.stroke();
      }

      // 5. Calculate Telemetry & Passed Stops
      const activePins = getCinemaSelectedPins();
      const numPins = activePins.length;
      let closestStop = null;
      let closestDist = 99999;
      let closestStopIndex = -1;
      let nextUpcomingStop = null;
      let nextUpcomingDistKm = 0;

      for (let index = 0; index < numPins; index++) {
        const pin = activePins[index];
        const wPt = latLngToMercatorWorld(pin.lat, pin.lng, vp.zoom);
        const pt = worldToScreen(wPt.x, wPt.y);

        const carScr = worldToScreen(curCarWorldX, curCarWorldY);
        const distToCar = Math.hypot(pt.x - carScr.x, pt.y - carScr.y);

        // Progress milestone & passed detection tailored to Journey Mode
        let targetPForPin = 0.5;
        let isPassed = false;

        if (cinemaJourneyMode === 'outbound') {
          targetPForPin = numPins > 1 ? (index / (numPins - 1)) : 0.5;
          isPassed = targetPForPin <= (progress + 0.02);
        } else if (cinemaJourneyMode === 'return') {
          const returnStep = numPins - 1 - index;
          targetPForPin = numPins > 1 ? (returnStep / (numPins - 1)) : 0.5;
          isPassed = targetPForPin <= (progress + 0.02);
        } else {
          // roundtrip
          if (progress <= 0.5) {
            const outboundProg = progress * 2.0;
            const mOutbound = numPins > 1 ? (index / (numPins - 1)) : 0.5;
            targetPForPin = mOutbound * 0.5;
            isPassed = mOutbound <= (outboundProg + 0.02);
          } else {
            const returnProg = (progress - 0.5) * 2.0;
            const returnStep = numPins - 1 - index;
            const mReturn = numPins > 1 ? (returnStep / (numPins - 1)) : 0.5;
            targetPForPin = 0.5 + (mReturn * 0.5);
            isPassed = true; // Visited on outbound
          }
        }

        const progressDiff = Math.abs(progress - targetPForPin);
        const isApproachingOrCurrent = (distToCar < (180 * uiScale)) || (numPins > 1 && progressDiff <= (0.75 / numPins));

        if (isApproachingOrCurrent && distToCar < closestDist) {
          closestDist = distToCar;
          closestStop = pin;
          closestStopIndex = index;
        }

        // Find next upcoming stop
        if (!isPassed && !nextUpcomingStop) {
          nextUpcomingStop = pin;
          const carGps = { lat: vp.carLat, lng: vp.carLng };
          nextUpcomingDistKm = parseFloat((getHaversineDistance(carGps.lat, carGps.lng, pin.lat, pin.lng) / 1000).toFixed(1));
        }

        // Draw Billboard Stop Badges on Map (if in viewport)
        if (pt.x >= -150 && pt.x <= w + 150 && pt.y >= -50 && pt.y <= h + 150) {
          // Ground pulse ring
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, (isPassed ? 15 : 12) * uiScale, 0, Math.PI * 2);
          ctx.fillStyle = isPassed ? 'rgba(16, 185, 129, 0.4)' : 'rgba(14, 165, 233, 0.35)';
          ctx.fill();

          // Ground pin core
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, (isPassed ? 9.5 : 8) * uiScale, 0, Math.PI * 2);
          ctx.fillStyle = isPassed ? '#10b981' : (pin.color || '#0ea5e9');
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2.4 * uiScale;
          ctx.fill();
          ctx.stroke();

          let photoImg = cinemaPinImageCache.get(pin.id) || cinemaPinImageCache.get(String(pin.id)) || (pin.photo ? cinemaPinImageCache.get(pin.photo) : null);
          if (!photoImg && pin.photo) {
            const lazyImg = new Image();
            if (!pin.photo.startsWith('data:') && !pin.photo.startsWith('blob:')) {
              lazyImg.crossOrigin = 'anonymous';
            }
            lazyImg.src = pin.photo;
            lazyImg.onload = () => {
              cinemaPinImageCache.set(pin.id, lazyImg);
              cinemaPinImageCache.set(String(pin.id), lazyImg);
              cinemaPinImageCache.set(pin.photo, lazyImg);
            };
            if (lazyImg.naturalWidth > 0) {
              photoImg = lazyImg;
            }
          }

          if (photoImg) {
            const photoW = 64 * uiScale;
            const photoH = 64 * uiScale;
            const photoX = pt.x - (photoW / 2);
            const photoY = pt.y - photoH - (26 * uiScale);

            // Stem line
            ctx.beginPath();
            ctx.moveTo(pt.x, pt.y);
            ctx.lineTo(pt.x, photoY + photoH);
            ctx.strokeStyle = isPassed ? '#10b981' : '#ffffff';
            ctx.lineWidth = 2.2 * uiScale;
            ctx.stroke();

            // Photo frame background
            ctx.fillStyle = '#0f172a';
            ctx.strokeStyle = isPassed ? '#10b981' : (pin.color || '#38bdf8');
            ctx.lineWidth = 2.5 * uiScale;
            roundRect(ctx, photoX, photoY, photoW, photoH, 12 * uiScale, true, true);

            // Draw cropped square image
            ctx.save();
            ctx.beginPath();
            roundRect(ctx, photoX + (2.5 * uiScale), photoY + (2.5 * uiScale), photoW - (5 * uiScale), photoH - (5 * uiScale), 10 * uiScale, false, false);
            ctx.clip();
            ctx.drawImage(photoImg, photoX + (2.5 * uiScale), photoY + (2.5 * uiScale), photoW - (5 * uiScale), photoH - (5 * uiScale));
            ctx.restore();

            // Badge number on top-left of photo
            const badgeW = 20 * uiScale;
            const badgeX = photoX - (4 * uiScale);
            const badgeY = photoY - (4 * uiScale);
            ctx.beginPath();
            ctx.arc(badgeX + (badgeW / 2), badgeY + (badgeW / 2), badgeW / 2, 0, Math.PI * 2);
            ctx.fillStyle = isPassed ? '#10b981' : (pin.color || '#6366f1');
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2 * uiScale;
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#ffffff';
            ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(isPassed ? '✓' : `${index + 1}`, badgeX + (badgeW / 2), badgeY + (badgeW / 2));

            // Title Pill below photo
            const labelText = pin.title || `Điểm #${index + 1}`;
            ctx.font = `bold ${Math.round(11.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
            const textMetrics = ctx.measureText(labelText);
            const pillW = Math.min(textMetrics.width + (18 * uiScale), 170 * uiScale);
            const pillH = 22 * uiScale;
            const pillX = pt.x - (pillW / 2);
            const pillY = photoY + photoH + (4 * uiScale);

            ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
            ctx.strokeStyle = isPassed ? 'rgba(16, 185, 129, 0.9)' : 'rgba(56, 189, 248, 0.9)';
            ctx.lineWidth = 1.4 * uiScale;
            roundRect(ctx, pillX, pillY, pillW, pillH, 7 * uiScale, true, true);

            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            let dispText = labelText;
            if (ctx.measureText(dispText).width > pillW - (12 * uiScale)) {
              while (dispText.length > 3 && ctx.measureText(dispText + '..').width > pillW - (12 * uiScale)) {
                dispText = dispText.substring(0, dispText.length - 1);
              }
              dispText += '..';
            }
            ctx.fillText(dispText, pt.x, pillY + (pillH / 2));
          } else {
            // Standard Upright Billboard Label Pill (no photo)
            const labelText = `${index + 1}. ${pin.title || 'Điểm'}`;
            ctx.font = `bold ${Math.round(12.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
            const textMetrics = ctx.measureText(labelText);
            const pillW = textMetrics.width + (22 * uiScale);
            const pillH = 28 * uiScale;
            const pillX = pt.x - (pillW / 2);
            const pillY = pt.y - (40 * uiScale);

            // Stem line
            ctx.beginPath();
            ctx.moveTo(pt.x, pt.y);
            ctx.lineTo(pt.x, pillY + pillH);
            ctx.strokeStyle = isPassed ? '#10b981' : '#ffffff';
            ctx.lineWidth = 2 * uiScale;
            ctx.stroke();

            ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
            ctx.strokeStyle = isPassed ? 'rgba(16, 185, 129, 0.9)' : (pin.color || 'rgba(99, 102, 241, 0.9)');
            ctx.lineWidth = 1.5 * uiScale;
            roundRect(ctx, pillX, pillY, pillW, pillH, 8 * uiScale, true, true);

            ctx.fillStyle = isPassed ? '#34d399' : '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(labelText, pt.x, pillY + (pillH / 2));
          }
        }
      }

      // 6. Draw Traveling Vehicle (Smooth Headlight Beams & Icon)
      const carScreenPos = worldToScreen(curCarWorldX, curCarWorldY);
      ctx.save();
      ctx.translate(carScreenPos.x, carScreenPos.y);
      ctx.rotate(vp.headingAngle);

      // Forward Headlight Beam
      const beamGrad = ctx.createLinearGradient(0, 0, 95 * uiScale, 0);
      beamGrad.addColorStop(0, 'rgba(56, 189, 248, 0.65)');
      beamGrad.addColorStop(0.4, 'rgba(56, 189, 248, 0.25)');
      beamGrad.addColorStop(1, 'rgba(56, 189, 248, 0)');
      ctx.fillStyle = beamGrad;
      ctx.beginPath();
      ctx.moveTo(10 * uiScale, 0);
      ctx.lineTo(95 * uiScale, -28 * uiScale);
      ctx.lineTo(95 * uiScale, 28 * uiScale);
      ctx.closePath();
      ctx.fill();

      // Outer Halo pulse
      ctx.beginPath();
      ctx.arc(0, 0, 26 * uiScale, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(14, 165, 233, 0.35)';
      ctx.fill();

      // Vehicle base circle
      ctx.beginPath();
      ctx.arc(0, 0, 16 * uiScale, 0, Math.PI * 2);
      ctx.fillStyle = '#0284c7';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3 * uiScale;
      ctx.fill();
      ctx.stroke();

      // Directional arrow
      ctx.beginPath();
      ctx.moveTo(11 * uiScale, 0);
      ctx.lineTo(-7 * uiScale, -9 * uiScale);
      ctx.lineTo(-3.5 * uiScale, 0);
      ctx.lineTo(-7 * uiScale, 9 * uiScale);
      ctx.closePath();
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.restore();

      // 7. Dynamic Telemetry Calculations
      const cActiveKm = c.cActiveJourneyKm || c.cOutboundKm || 1.0;
      const cTimeStr = c.cTimeStr || '0 phút';
      const cProvInfo = c.cProvInfo || { count: 1, list: [] };
      const active = getCinemaSelectedRoute();
      const isMultiCinema = cinemaTargetRouteId === 'all';
      const travelMode = (active && active.travelMode) || 'driving';
      const isMotorcycle = travelMode === 'motorcycle';

      const modeBadge = cinemaCameraMode === 'follow' ? '🎥 Cận cảnh' : (cinemaCameraMode === 'cinematic' ? '🎬 Điện ảnh' : '🗺️ Toàn cảnh');
      const jBadge = cinemaJourneyMode === 'return' ? '🔄 1 Lượt về (B ➔ A)' : (cinemaJourneyMode === 'outbound' ? '🏁 1 Lượt (A ➔ B)' : '🌟 Khứ hồi (A ➔ B ➔ A)');
      const jBadgeShort = cinemaJourneyMode === 'return' ? '🔄 1 Lượt về' : (cinemaJourneyMode === 'outbound' ? '🏁 1 Lượt' : '🌟 Khứ hồi');
      const vehicleBadge = isMotorcycle ? '🛵 Xe máy' : '🚗 Ô tô';
      const routeDisplayName = isMultiCinema ? `Trọn bộ ${routes.length} tuyến` : (active ? (active.name || 'Lộ trình') : 'Lộ trình');

      // Live Traveled & Remaining stats
      const liveTraveledKm = parseFloat((cActiveKm * progress).toFixed(1));
      const liveRemainingKm = parseFloat(Math.max(0, cActiveKm - liveTraveledKm).toFixed(1));
      const liveProgressPct = Math.min(100, Math.max(0, Math.round(progress * 100)));

      // Dynamic Speed Simulation (Realistic curve & stop slowdown)
      let baseSpeed = isMotorcycle ? 48 : 65;
      if (closestStop && closestDist < 120 * uiScale) {
        // Slow down smoothly when near stops
        baseSpeed = isMotorcycle ? 28 : 35;
      } else {
        // Natural slight speed fluctuation
        const speedWobble = Math.sin(progress * 40) * (isMotorcycle ? 5 : 8);
        baseSpeed = Math.round(baseSpeed + speedWobble);
      }
      const liveSpeedText = `${baseSpeed} km/h`;

      // Count passed stops
      let passedCount = 0;
      if (numPins > 0) {
        passedCount = Math.min(numPins, Math.max(1, Math.floor(progress * numPins) + 1));
      }

      // =========================================================================
      // 8. MASTER TOP HEADER HUD (Crystal Clear, High Contrast, Responsive Design)
      // =========================================================================
      if (isPortrait) {
        // PORTRAIT TOP HUD (Full-width unified glass card with 2 clear rows)
        const headerW = w - (36 * uiScale);
        const headerH = 112 * uiScale;
        const headerX = 18 * uiScale;
        const headerY = 24 * uiScale;

        // Glass background with soft inner glow
        ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.lineWidth = 1.5 * uiScale;
        roundRect(ctx, headerX, headerY, headerW, headerH, 16 * uiScale, true, true);

        // Row 1: Brand pill + Route Name + Mode Tags
        // Brand Pill
        const bPillW = 92 * uiScale;
        const bPillH = 22 * uiScale;
        ctx.fillStyle = 'rgba(14, 165, 233, 0.25)';
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1 * uiScale;
        roundRect(ctx, headerX + (14 * uiScale), headerY + (12 * uiScale), bPillW, bPillH, 6 * uiScale, true, true);

        ctx.fillStyle = '#38bdf8';
        ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('📍 GẠO MAPS', headerX + (14 * uiScale) + (bPillW / 2), headerY + (12 * uiScale) + (bPillH / 2));

        // Route Title (Bold, Crisp White)
        ctx.textAlign = 'left';
        ctx.font = `bold ${Math.round(14.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.fillStyle = '#ffffff';
        let rTitleText = routeDisplayName;
        const maxTitleW = headerW - bPillW - (130 * uiScale);
        if (ctx.measureText(rTitleText).width > maxTitleW) {
          while (rTitleText.length > 3 && ctx.measureText(rTitleText + '..').width > maxTitleW) {
            rTitleText = rTitleText.substring(0, rTitleText.length - 1);
          }
          rTitleText += '..';
        }
        ctx.fillText(rTitleText, headerX + (14 * uiScale) + bPillW + (10 * uiScale), headerY + (12 * uiScale) + (bPillH / 2));

        // Mode Pill on Right
        ctx.textAlign = 'right';
        ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.fillStyle = '#fde047';
        ctx.fillText(`${vehicleBadge} • ${jBadgeShort}`, headerX + headerW - (14 * uiScale), headerY + (12 * uiScale) + (bPillH / 2));

        // Divider line
        ctx.beginPath();
        ctx.moveTo(headerX + (14 * uiScale), headerY + (44 * uiScale));
        ctx.lineTo(headerX + headerW - (14 * uiScale), headerY + (44 * uiScale));
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 1 * uiScale;
        ctx.stroke();

        // Row 2: 4-Pillar Telemetry Grid
        const colW = (headerW - (28 * uiScale)) / 4;
        const metrics = [
          { label: 'QUÃNG ĐƯỜNG', val: `${cActiveKm.toLocaleString('vi-VN')} km`, color: '#38bdf8' },
          { label: 'THỜI GIAN', val: `~${cTimeStr}`, color: '#fde047' },
          { label: 'ĐIỂM DỪNG', val: `${passedCount}/${numPins} điểm`, color: '#34d399' },
          { label: 'ĐỊA PHẬN', val: `${cProvInfo.count} Tỉnh/TP`, color: '#c084fc' }
        ];

        metrics.forEach((m, idx) => {
          const colX = headerX + (14 * uiScale) + (idx * colW);
          const colCenter = colX + (colW / 2);

          // Sub-label
          ctx.fillStyle = '#94a3b8';
          ctx.font = `bold ${Math.round(9.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(m.label, colCenter, headerY + (52 * uiScale));

          // Big value
          ctx.fillStyle = m.color;
          ctx.font = `bold ${Math.round(13 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
          ctx.fillText(m.val, colCenter, headerY + (72 * uiScale));

          // Vertical separator
          if (idx < 3) {
            ctx.beginPath();
            ctx.moveTo(colX + colW, headerY + (52 * uiScale));
            ctx.lineTo(colX + colW, headerY + (98 * uiScale));
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
            ctx.lineWidth = 1 * uiScale;
            ctx.stroke();
          }
        });

      } else {
        // LANDSCAPE TOP HUD (Two Balanced High-Contrast Glass Cards)
        // 1. Left Card: Route Branding & Tags
        const brandW = Math.min(460 * uiScale, w * 0.44);
        const brandH = 80 * uiScale;
        const brandX = 24 * uiScale;
        const brandY = 24 * uiScale;

        ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.lineWidth = 1.5 * uiScale;
        roundRect(ctx, brandX, brandY, brandW, brandH, 16 * uiScale, true, true);

        // Brand Pill
        const bPillW = 88 * uiScale;
        const bPillH = 20 * uiScale;
        ctx.fillStyle = 'rgba(14, 165, 233, 0.25)';
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1 * uiScale;
        roundRect(ctx, brandX + (14 * uiScale), brandY + (12 * uiScale), bPillW, bPillH, 5 * uiScale, true, true);

        ctx.fillStyle = '#38bdf8';
        ctx.font = `bold ${Math.round(10.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('📍 GẠO MAPS', brandX + (14 * uiScale) + (bPillW / 2), brandY + (12 * uiScale) + (bPillH / 2));

        // Sub tags
        ctx.textAlign = 'left';
        ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.fillStyle = '#fde047';
        ctx.fillText(`${vehicleBadge} • ${jBadge}`, brandX + (14 * uiScale) + bPillW + (10 * uiScale), brandY + (12 * uiScale) + (bPillH / 2));

        // Route Title (Big White)
        ctx.font = `bold ${Math.round(15.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.fillStyle = '#ffffff';
        ctx.textBaseline = 'top';
        let rTitleText = routeDisplayName;
        const maxTitleW = brandW - (28 * uiScale);
        if (ctx.measureText(rTitleText).width > maxTitleW) {
          while (rTitleText.length > 3 && ctx.measureText(rTitleText + '..').width > maxTitleW) {
            rTitleText = rTitleText.substring(0, rTitleText.length - 1);
          }
          rTitleText += '..';
        }
        ctx.fillText(rTitleText, brandX + (14 * uiScale), brandY + (42 * uiScale));

        // 2. Right Card: Telemetry Grid HUD
        const hudW = Math.min(500 * uiScale, w * 0.47);
        const hudH = 80 * uiScale;
        const hudX = w - hudW - (24 * uiScale);
        const hudY = 24 * uiScale;

        ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.lineWidth = 1.5 * uiScale;
        roundRect(ctx, hudX, hudY, hudW, hudH, 16 * uiScale, true, true);

        // 4 Columns in HUD
        const colW = (hudW - (24 * uiScale)) / 4;
        const hudMetrics = [
          { label: 'QUÃNG ĐƯỜNG', val: `${cActiveKm.toLocaleString('vi-VN')} km`, color: '#38bdf8' },
          { label: 'THỜI GIAN', val: `~${cTimeStr}`, color: '#fde047' },
          { label: 'TIẾN ĐỘ', val: `${passedCount}/${numPins} điểm`, color: '#34d399' },
          { label: 'ĐỊA PHẬN', val: `${cProvInfo.count} Tỉnh/TP`, color: '#c084fc' }
        ];

        hudMetrics.forEach((m, idx) => {
          const colX = hudX + (12 * uiScale) + (idx * colW);
          const colCenter = colX + (colW / 2);

          ctx.fillStyle = '#94a3b8';
          ctx.font = `bold ${Math.round(9.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(m.label, colCenter, hudY + (16 * uiScale));

          ctx.fillStyle = m.color;
          ctx.font = `bold ${Math.round(13 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
          ctx.fillText(m.val, colCenter, hudY + (42 * uiScale));

          if (idx < 3) {
            ctx.beginPath();
            ctx.moveTo(colX + colW, hudY + (16 * uiScale));
            ctx.lineTo(colX + colW, hudY + (64 * uiScale));
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 1 * uiScale;
            ctx.stroke();
          }
        });
      }

      // =========================================================================
      // 9. STOP ARRIVAL CINEMATIC CARD (High-Fidelity Pop-up when approaching stop)
      // =========================================================================
      if (closestStop) {
        const stopIdx = closestStopIndex >= 0 ? closestStopIndex : activePins.findIndex(p => p.id === closestStop.id);
        let stopPhotoImg = cinemaPinImageCache.get(closestStop.id) || cinemaPinImageCache.get(String(closestStop.id)) || (closestStop.photo ? cinemaPinImageCache.get(closestStop.photo) : null);
        const catConfig = CATEGORIES[closestStop.category] || CATEGORIES.sightseeing;

        const cardW = isPortrait ? (w - (36 * uiScale)) : Math.min(460 * uiScale, w * 0.44);
        const cardH = 96 * uiScale;
        const cardX = isPortrait ? (18 * uiScale) : (24 * uiScale);
        const cardY = isPortrait ? (148 * uiScale) : (116 * uiScale);

        // Card background
        ctx.fillStyle = 'rgba(10, 15, 30, 0.96)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.8)';
        ctx.lineWidth = 1.8 * uiScale;
        roundRect(ctx, cardX, cardY, cardW, cardH, 16 * uiScale, true, true);

        let textStartX = cardX + (16 * uiScale);

        if (stopPhotoImg || closestStop.photo) {
          if (!stopPhotoImg && closestStop.photo) {
            const tempImg = new Image();
            tempImg.src = closestStop.photo;
            if (tempImg.naturalWidth > 0) stopPhotoImg = tempImg;
          }
          if (stopPhotoImg) {
            const imgSize = cardH - (18 * uiScale);
            const imgX = cardX + (9 * uiScale);
            const imgY = cardY + (9 * uiScale);

            ctx.save();
            roundRect(ctx, imgX, imgY, imgSize, imgSize, 12 * uiScale, false, false);
            ctx.clip();
            ctx.drawImage(stopPhotoImg, imgX, imgY, imgSize, imgSize);
            ctx.restore();

            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2 * uiScale;
            roundRect(ctx, imgX, imgY, imgSize, imgSize, 12 * uiScale, false, true);

            textStartX = imgX + imgSize + (14 * uiScale);
          }
        }

        const availTextW = cardX + cardW - textStartX - (14 * uiScale);

        // Line 1: Stop Milestone Tag
        let stopBadgeLine1 = '';
        if (cinemaJourneyMode === 'outbound') {
          if (stopIdx === 0) stopBadgeLine1 = '🏁 XUẤT PHÁT: ĐIỂM #1';
          else if (stopIdx === numPins - 1) stopBadgeLine1 = `🏆 ĐÍCH ĐẾN: ĐIỂM #${numPins}`;
          else stopBadgeLine1 = `📍 ĐIỂM DỪNG #${stopIdx + 1}`;
        } else if (cinemaJourneyMode === 'return') {
          if (stopIdx === numPins - 1) stopBadgeLine1 = `🔄 XUẤT PHÁT CHIỀU VỀ: ĐIỂM #${numPins}`;
          else if (stopIdx === 0) stopBadgeLine1 = '🏆 VỀ ĐÍCH: ĐIỂM #1';
          else stopBadgeLine1 = `🔄 CHIỀU VỀ: ĐIỂM #${stopIdx + 1}`;
        } else {
          // roundtrip
          if (progress <= 0.5) {
            if (stopIdx === 0) stopBadgeLine1 = '🏁 XUẤT PHÁT LƯỢT ĐI: ĐIỂM #1';
            else if (stopIdx === numPins - 1) stopBadgeLine1 = `🌟 QUAY ĐẦU: ĐIỂM #${numPins}`;
            else stopBadgeLine1 = `📍 LƯỢT ĐI: ĐIỂM #${stopIdx + 1}`;
          } else {
            if (stopIdx === 0) stopBadgeLine1 = '🎉 VỀ ĐÍCH KHỨ HỒI: ĐIỂM #1';
            else if (stopIdx === numPins - 1) stopBadgeLine1 = `🔄 BẮT ĐẦU LƯỢT VỀ: ĐIỂM #${numPins}`;
            else stopBadgeLine1 = `🔄 LƯỢT VỀ: ĐIỂM #${stopIdx + 1}`;
          }
        }
        stopBadgeLine1 += ` • ${catConfig.name.toUpperCase()}`;

        ctx.fillStyle = '#38bdf8';
        ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(stopBadgeLine1, textStartX, cardY + (14 * uiScale));

        // Line 2: Stop Title
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.round(15.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        let dispTitle = closestStop.title || `Điểm #${stopIdx + 1}`;
        if (ctx.measureText(dispTitle).width > availTextW) {
          while (dispTitle.length > 3 && ctx.measureText(dispTitle + '..').width > availTextW) {
            dispTitle = dispTitle.substring(0, dispTitle.length - 1);
          }
          dispTitle += '..';
        }
        ctx.fillText(dispTitle, textStartX, cardY + (36 * uiScale));

        // Line 3: Location / Notes / Rating
        ctx.fillStyle = '#cbd5e1';
        ctx.font = `${Math.round(11.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        let dispSub = closestStop.notes || closestStop.locationName || 'Điểm check-in trên lộ trình';
        if (closestStop.rating) {
          dispSub = `⭐ ${closestStop.rating}/5 • ` + dispSub;
        }
        if (ctx.measureText(dispSub).width > availTextW) {
          while (dispSub.length > 3 && ctx.measureText(dispSub + '..').width > availTextW) {
            dispSub = dispSub.substring(0, dispSub.length - 1);
          }
          dispSub += '..';
        }
        ctx.fillText(dispSub, textStartX, cardY + (64 * uiScale));

        // Update DOM popup for live web preview
        const popupEl = document.getElementById('cinema-stop-popup');
        if (popupEl) {
          popupEl.classList.remove('hidden');
          const popNum = document.getElementById('cinema-popup-num');
          if (popNum) popNum.textContent = `${stopIdx + 1}`;
          const popTitle = document.getElementById('cinema-popup-title');
          if (popTitle) popTitle.textContent = closestStop.title || `Điểm #${stopIdx + 1}`;
          const popCat = document.getElementById('cinema-popup-cat');
          if (popCat) popCat.textContent = catConfig.name;
          const popNotes = document.getElementById('cinema-popup-notes');
          if (popNotes) popNotes.textContent = closestStop.notes || closestStop.locationName || 'Điểm check-in trong lộ trình Gạo Maps';
          const imgWrap = document.getElementById('cinema-popup-img-wrap');
          const imgEl = document.getElementById('cinema-popup-img');
          const stopPhoto = closestStop.photo || (typeof getPhotoForPin === 'function' ? getPhotoForPin(closestStop) : null);
          if (stopPhoto && imgWrap && imgEl) {
            imgEl.src = stopPhoto;
            imgWrap.classList.remove('hidden');
          } else if (imgWrap) {
            imgWrap.classList.add('hidden');
          }
        }
      } else {
        const popupEl = document.getElementById('cinema-stop-popup');
        if (popupEl) {
          popupEl.classList.add('hidden');
        }
      }

      // =========================================================================
      // 10. MINI-MAP RADAR INSET (Downsampled & Highly Stylized)
      // =========================================================================
      let radarW = 0;
      let radarH = 0;
      let radarX = 0;
      let radarY = 0;

      if (cinemaCameraMode !== 'overview') {
        radarW = isPortrait ? (240 * uiScale) : (210 * uiScale);
        radarH = isPortrait ? (160 * uiScale) : (145 * uiScale);
        radarX = w - radarW - (20 * uiScale);
        radarY = h - radarH - (28 * uiScale);

        ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
        ctx.lineWidth = 1.5 * uiScale;
        roundRect(ctx, radarX, radarY, radarW, radarH, 14 * uiScale, true, true);

        // Header inside radar
        ctx.fillStyle = '#38bdf8';
        ctx.font = `bold ${Math.round(10.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText('📡 RADAR', radarX + (12 * uiScale), radarY + (10 * uiScale));

        ctx.fillStyle = 'rgba(226, 232, 240, 0.85)';
        ctx.font = `bold ${Math.round(10 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = 'right';
        ctx.fillText(`${liveProgressPct}% • ${isTilt ? cinemaTiltAngle + '°' : '2D'}`, radarX + radarW - (12 * uiScale), radarY + (10 * uiScale));

        const padR = 14 * uiScale;
        const availRW = radarW - padR * 2;
        const availRH = radarH - padR * 2 - (20 * uiScale);
        const latSpan = Math.max(c.maxLat - c.minLat, 0.005);
        const lngSpan = Math.max(c.maxLng - c.minLng, 0.005);

        function mapToRadar(lat, lng) {
          return {
            x: radarX + padR + ((lng - c.minLng) / lngSpan) * availRW,
            y: radarY + radarH - padR - ((lat - c.minLat) / latSpan) * availRH
          };
        }

        const radarStep = Math.max(1, Math.floor(pathCoords.length / 150));

        // Inactive trail
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.lineWidth = 3 * uiScale;
        let isFirst = true;
        for (let i = 0; i < pathCoords.length; i += radarStep) {
          const rP = mapToRadar(pathCoords[i].lat, pathCoords[i].lng);
          if (isFirst) { ctx.moveTo(rP.x, rP.y); isFirst = false; }
          else ctx.lineTo(rP.x, rP.y);
        }
        ctx.stroke();

        // Active glowing trail
        ctx.beginPath();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3.8 * uiScale;
        isFirst = true;
        for (let i = 0; i <= currentIdx; i += radarStep) {
          const rP = mapToRadar(pathCoords[i].lat, pathCoords[i].lng);
          if (isFirst) { ctx.moveTo(rP.x, rP.y); isFirst = false; }
          else ctx.lineTo(rP.x, rP.y);
        }
        const rCarP = mapToRadar(vp.carLat, vp.carLng);
        ctx.lineTo(rCarP.x, rCarP.y);
        ctx.stroke();

        // Waypoints in radar
        activePins.forEach(pin => {
          const rPinP = mapToRadar(pin.lat, pin.lng);
          ctx.beginPath();
          ctx.arc(rPinP.x, rPinP.y, 3.5 * uiScale, 0, Math.PI * 2);
          ctx.fillStyle = '#10b981';
          ctx.fill();
        });

        // Vehicle beacon in radar
        ctx.beginPath();
        ctx.arc(rCarP.x, rCarP.y, 5 * uiScale, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.8 * uiScale;
        ctx.fill();
        ctx.stroke();
      }

      // =========================================================================
      // 11. LIVE FLOATING COCKPIT TELEMETRY BAR (Speedometer, Traveled Km & Target)
      // =========================================================================
      let cockW, cockH, cockX, cockY;
      if (isPortrait) {
        cockW = w - radarW - (48 * uiScale);
        cockH = 84 * uiScale;
        cockX = 18 * uiScale;
        cockY = h - cockH - (28 * uiScale);
      } else {
        cockW = Math.min(480 * uiScale, w * 0.44);
        cockH = 80 * uiScale;
        cockX = 24 * uiScale;
        cockY = h - cockH - (28 * uiScale);
      }

      // Cockpit Bar Background
      ctx.fillStyle = 'rgba(10, 15, 30, 0.94)';
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
      ctx.lineWidth = 1.5 * uiScale;
      roundRect(ctx, cockX, cockY, cockW, cockH, 16 * uiScale, true, true);

      // Speedometer Gauge on Left
      const speedGaugeW = 76 * uiScale;
      const speedGaugeH = cockH - (20 * uiScale);
      const speedGaugeX = cockX + (10 * uiScale);
      const speedGaugeY = cockY + (10 * uiScale);

      ctx.fillStyle = 'rgba(14, 165, 233, 0.15)';
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
      ctx.lineWidth = 1.2 * uiScale;
      roundRect(ctx, speedGaugeX, speedGaugeY, speedGaugeW, speedGaugeH, 10 * uiScale, true, true);

      // Speed Icon & Label
      ctx.fillStyle = '#38bdf8';
      ctx.font = `bold ${Math.round(9.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText('TỐC ĐỘ', speedGaugeX + (speedGaugeW / 2), speedGaugeY + (6 * uiScale));

      // Speed Value
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${Math.round(14.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
      ctx.fillText(liveSpeedText, speedGaugeX + (speedGaugeW / 2), speedGaugeY + (24 * uiScale));

      // Real-time Traveled Metrics (Right of Speedometer)
      const cockInfoX = speedGaugeX + speedGaugeW + (14 * uiScale);
      const cockAvailW = cockX + cockW - cockInfoX - (12 * uiScale);

      // Line 1: Live Traveled Km + Progress Badge
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.font = `bold ${Math.round(13 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
      ctx.fillStyle = '#38bdf8';
      ctx.fillText('📍 Đã đi: ', cockInfoX, cockY + (14 * uiScale));

      const traLabW = ctx.measureText('📍 Đã đi: ').width;
      ctx.fillStyle = '#ffffff';
      ctx.fillText(`${liveTraveledKm} / ${cActiveKm.toLocaleString('vi-VN')} km`, cockInfoX + traLabW, cockY + (14 * uiScale));

      // Progress Pill
      const progBadgeX = cockX + cockW - (64 * uiScale);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 1 * uiScale;
      roundRect(ctx, progBadgeX, cockY + (12 * uiScale), 52 * uiScale, 20 * uiScale, 5 * uiScale, true, true);

      ctx.fillStyle = '#34d399';
      ctx.font = `bold ${Math.round(10.5 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${liveProgressPct}%`, progBadgeX + (26 * uiScale), cockY + (22 * uiScale));

      // Line 2: Next Destination or Target info
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.font = `bold ${Math.round(11 * uiScale)}px 'Plus Jakarta Sans', sans-serif`;

      let targetLabel = '';
      if (nextUpcomingStop) {
        targetLabel = `➡️ Tiếp theo: ${nextUpcomingStop.title || 'Điểm dừng'} (~${nextUpcomingDistKm} km)`;
      } else if (progress > 0.95) {
        targetLabel = '🏆 Chuẩn bị về đích an toàn!';
      } else {
        targetLabel = '🛣️ Đang lăn bánh trên lộ trình';
      }

      ctx.fillStyle = '#fde047';
      if (ctx.measureText(targetLabel).width > cockAvailW) {
        while (targetLabel.length > 3 && ctx.measureText(targetLabel + '..').width > cockAvailW) {
          targetLabel = targetLabel.substring(0, targetLabel.length - 1);
        }
        targetLabel += '..';
      }
      ctx.fillText(targetLabel, cockInfoX, cockY + (44 * uiScale));

      // =========================================================================
      // 12. BOTTOM NEON GLOW PROGRESS LINE
      // =========================================================================
      const barH = 5 * uiScale;
      const barY = h - barH;

      // Dark track
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.fillRect(0, barY, w, barH);

      // Active progress gradient fill
      const pFillW = w * progress;
      if (pFillW > 0) {
        const barGrad = ctx.createLinearGradient(0, 0, w, 0);
        barGrad.addColorStop(0, '#0284c7');
        barGrad.addColorStop(0.5, '#38bdf8');
        barGrad.addColorStop(1, '#34d399');
        ctx.fillStyle = barGrad;
        ctx.fillRect(0, barY, pFillW, barH);

        // Leading glowing indicator dot
        ctx.beginPath();
        ctx.arc(pFillW, barY + (barH / 2), 4 * uiScale, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
      }
    }'''

start_idx = text.find('function drawCinemaFrame(progress, pathCoords) {')
end_idx = text.find('function loadImageHelper(src) {')

if start_idx != -1 and end_idx != -1:
    new_text = text[:start_idx] + draw_func_code + '\n\n    ' + text[end_idx:]
    with open('index.html', 'w', encoding='utf-8') as f_out:
        f_out.write(new_text)
    print('drawCinemaFrame replaced successfully in index.html!')
else:
    print('Error: Boundary not found')
