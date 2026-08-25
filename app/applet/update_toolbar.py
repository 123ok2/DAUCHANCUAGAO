import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Toolbar HTML for Aspect Ratio, Journey Mode, and HUD selector
old_toolbar_chunk = '''          <!-- Video Aspect Ratio (Vertical 9:16 vs Landscape 16:9 vs Square 1:1) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-rose-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Khung hình video: Dọc 9:16 (TikTok/Reels/Shorts) hoặc Ngang 16:9 (YouTube)">
            <i class="fa-solid fa-mobile-screen-button text-[11px] sm:text-xs text-rose-400 shrink-0"></i>
            <span class="text-[10px] sm:text-[11px] font-bold text-rose-300 hidden xs:inline">Khung hình:</span>
            <select id="cinema-aspect-select" onchange="changeCinemaAspectRatio(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-rose-200 outline-none cursor-pointer">
              <option value="9:16" class="bg-slate-900 text-rose-300" selected>📱 Dọc 9:16 (Shorts/Reels/TikTok)</option>
              <option value="16:9" class="bg-slate-900 text-white">💻 Ngang 16:9 (YouTube/HD)</option>
              <option value="1:1" class="bg-slate-900 text-white">⏹️ Vuông 1:1 (Instagram)</option>
            </select>
          </div>

          <!-- Journey Mode (Roundtrip vs Outbound vs Return) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-emerald-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Chế độ mô phỏng hành trình (Điểm 1 là nơi xuất phát và về đích khi khứ hồi)">
            <i class="fa-solid fa-arrows-spin text-[11px] sm:text-xs text-emerald-400 shrink-0"></i>
            <select id="cinema-journey-select" onchange="changeCinemaJourneyMode(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-emerald-300 outline-none cursor-pointer">
              <option value="roundtrip" class="bg-slate-900 text-emerald-400" selected>🌟 Khứ hồi (Đi & Về đích điểm 1)</option>
              <option value="outbound" class="bg-slate-900 text-white">🏁 Chiều đi (1 ➔ N)</option>
              <option value="return" class="bg-slate-900 text-white">🔄 Chiều về (N ➔ 1)</option>
            </select>
          </div>'''

new_toolbar_chunk = '''          <!-- Video Aspect Ratio (Vertical 9:16 vs Landscape 16:9 vs Square 1:1 vs Portrait 4:5) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-rose-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Khung hình video: Dọc 9:16 (TikTok/Reels/Shorts), Ngang 16:9 (YouTube), Vuông 1:1, Dọc 4:5">
            <i class="fa-solid fa-mobile-screen-button text-[11px] sm:text-xs text-rose-400 shrink-0"></i>
            <span class="text-[10px] sm:text-[11px] font-bold text-rose-300 hidden xs:inline">Khung hình:</span>
            <select id="cinema-aspect-select" onchange="changeCinemaAspectRatio(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-rose-200 outline-none cursor-pointer">
              <option value="9:16" class="bg-slate-900 text-rose-300" selected>📱 Dọc 9:16 (Shorts/Reels/TikTok)</option>
              <option value="16:9" class="bg-slate-900 text-white">💻 Ngang 16:9 (YouTube/HD)</option>
              <option value="1:1" class="bg-slate-900 text-white">⏹️ Vuông 1:1 (Instagram)</option>
              <option value="4:5" class="bg-slate-900 text-white">📸 Dọc 4:5 (Instagram Feed)</option>
            </select>
          </div>

          <!-- Journey Mode (Outbound 1 pass, Return 1 pass, Roundtrip 2 passes) -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-emerald-500/50 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Chế độ hành trình: Chiều đi (1 lượt), Chiều về (1 lượt), Khứ hồi (2 lượt Đi & Về)">
            <i class="fa-solid fa-arrows-spin text-[11px] sm:text-xs text-emerald-400 shrink-0"></i>
            <span class="text-[10px] sm:text-[11px] font-bold text-emerald-300 hidden xs:inline">Hành trình:</span>
            <select id="cinema-journey-select" onchange="changeCinemaJourneyMode(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-emerald-300 outline-none cursor-pointer">
              <option value="outbound" class="bg-slate-900 text-emerald-400" selected>🏁 Chiều đi (1 lượt • 1 ➔ N)</option>
              <option value="return" class="bg-slate-900 text-white">🔄 Chiều về (1 lượt • N ➔ 1)</option>
              <option value="roundtrip" class="bg-slate-900 text-amber-300">🌟 Khứ hồi (2 lượt • Đi & Về)</option>
            </select>
          </div>

          <!-- HUD Telemetry Display Customizer -->
          <div class="flex items-center gap-1 sm:gap-1.5 bg-slate-950/90 border border-sky-500/40 rounded-xl px-2 sm:px-2.5 py-1.5 shadow-inner shrink-0" title="Tùy biến hiển thị thông số chèn vào video">
            <i class="fa-solid fa-sliders text-[11px] sm:text-xs text-sky-400 shrink-0"></i>
            <span class="text-[10px] sm:text-[11px] font-bold text-sky-300 hidden xs:inline">Thông số:</span>
            <select id="cinema-hud-select" onchange="changeCinemaHudStyle(this.value)" class="bg-transparent text-[11px] sm:text-xs font-black text-sky-200 outline-none cursor-pointer">
              <option value="full" class="bg-slate-900 text-sky-300" selected>📊 Đầy đủ (Pro HUD)</option>
              <option value="compact" class="bg-slate-900 text-white">⚡ Gọn gàng (Mini HUD)</option>
              <option value="minimal" class="bg-slate-900 text-white">🎬 Tối giản (Chỉ Logo)</option>
            </select>
          </div>'''

if old_toolbar_chunk in content:
    content = content.replace(old_toolbar_chunk, new_toolbar_chunk, 1)
    print("Updated toolbar HTML successfully")
else:
    print("Warning: old_toolbar_chunk not found in content")

# 2. Update the video export overlay labels and badges
content = content.replace('<span>30 FPS • 4.5 Mbps</span>', '<span>60 FPS • 8.0 Mbps • Full HD</span>')
content = content.replace('<span>REC • ĐANG GHI VIDEO</span>', '<span id="cinema-rec-fps-label">REC • 60 FPS SIÊU MƯỢT</span>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Toolbar updates completed.")
