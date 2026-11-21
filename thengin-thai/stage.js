// The theatre around the cloth (portrait): lacquered lintel, posts, stage lip, warm spill on the inner edges. Drawn on the front layer.
export function drawFrame(g, Cam, spill = 1) {
  g.save(); g.setTransform(Cam[0], Cam[1], Cam[2], Cam[3], Cam[4], Cam[5]);
  const lac = '#2a0d08', lac2 = '#46140c', gold = '#8a6430';
  g.fillStyle = lac; g.fillRect(-600, -700, 2280, 700);
  g.fillStyle = lac2; g.fillRect(-300, -210, 1680, 170);
  g.strokeStyle = gold; g.lineWidth = 3;
  for (let x = -260; x < 1300; x += 110) { g.beginPath(); for (let i = 0; i <= 30; i++) { const a = i / 30 * Math.PI * 2.1, r = 30 * (1 - i / 30 * .75); const px = x + 55 + Math.cos(a) * r, py = -125 + Math.sin(a) * r * .7; if (i) g.lineTo(px, py); else g.moveTo(px, py); } g.stroke(); }
  g.beginPath(); g.moveTo(-300, -210); g.lineTo(1380, -210); g.moveTo(-300, -40); g.lineTo(1380, -40); g.stroke();
  g.fillStyle = '#6a1a10'; g.fillRect(-300, -40, 1680, 40);
  for (const x of [-210, 1080]) {
    const gr = g.createLinearGradient(x, 0, x + 210, 0); gr.addColorStop(0, '#1a0806'); gr.addColorStop(.5, '#3e110a'); gr.addColorStop(1, '#1a0806');
    g.fillStyle = gr; g.fillRect(x, -700, 210, 3400);
    g.strokeStyle = gold; g.lineWidth = 2.5; g.strokeRect(x + 22, 60, 166, 1800);
  }
  g.fillStyle = lac; g.fillRect(-600, 1920, 2280, 900);
  g.fillStyle = '#5a170d'; g.fillRect(-300, 1920, 1680, 50);
  g.strokeStyle = gold; g.lineWidth = 2.5; g.beginPath(); g.moveTo(-300, 1970); g.lineTo(1380, 1970); g.stroke();
  g.globalCompositeOperation = 'lighter';
  const sp = (x0, y0, x1, y1, gx0, gy0, gx1, gy1) => { const gr = g.createLinearGradient(gx0, gy0, gx1, gy1); gr.addColorStop(0, `rgba(255,170,90,${.3 * spill})`); gr.addColorStop(1, 'rgba(255,150,70,0)'); g.fillStyle = gr; g.fillRect(x0, y0, x1 - x0, y1 - y0); };
  sp(-300, -130, 1380, 0, 0, 0, 0, -130); sp(-300, 1920, 1380, 2060, 0, 1920, 0, 2060); sp(-170, -40, 0, 1960, 0, 0, -170, 0); sp(1080, -40, 1250, 1960, 1080, 0, 1250, 0);
  g.restore();
}
