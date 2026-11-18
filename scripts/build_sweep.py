"""
DNF 扫荡挂机 · 冒烟进度条 H5 · 构建脚本
用真实 DNF 精灵素材，做一个自动扫荡副本 + 冒烟进度条界面。单文件、无依赖。

用法：  python scripts/build_sweep.py
产物：  dist/dnf-sweep-idle.html
"""
import base64, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


def data_url(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return "data:image/%s;base64,%s" % ("jpeg" if ext == "jpg" else ext, b64)


def frames(dir_name, indices):
    return [data_url(os.path.join(ASSETS, dir_name, "%d.png" % i)) for i in indices]


sprites = {
    "player": {
        "idle":   frames("player", list(range(72, 81))),
        "attack": frames("player", list(range(0, 10))),
    },
    "goblin": {
        "idle":   frames("goblin", list(range(10, 16))),
        "hurt":   frames("goblin", [8, 9]),
    },
    "boss": {
        "idle":   frames("boss", list(range(21, 32))),
        "hurt":   frames("boss", list(range(16, 20))),
    },
}
bg = data_url(os.path.join(ASSETS, "bg.png"))

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>DNF 扫荡挂机 · 冒烟进度条</title>
<style>
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body{ margin:0; height:100%; background:#0b0d10; overflow:hidden;
             font-family:"Microsoft YaHei",sans-serif; color:#e8e2d4; }
  #wrap{ position:relative; width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
  canvas{ display:block; width:100%; height:100%; object-fit:contain; background:#000; }
</style>
</head>
<body>
<div id="wrap"><canvas id="game" width="1000" height="620"></canvas></div>
<script>
const SPR = __SPRITES_JSON__;
const BG = __BG_DATA__;
const cv = document.getElementById('game'), ctx = cv.getContext('2d');
const W = cv.width, H = cv.height;

function load(src){ const i=new Image(); i.src=src; return i; }
for (const k in SPR) for (const a in SPR[k]) SPR[k][a]=SPR[k][a].map(load);
const bgImg = load(BG);

// ---------- 副本配置 ----------
const DUNGEONS = [
  {name:'幽暗密林',   monster:'goblin', mname:'哥布林',     lv:5,  rounds:10, hp:120, gold:1200,  exp:800},
  {name:'雷鸣废墟',   monster:'goblin', mname:'哥布林十夫长',lv:17, rounds:15, hp:260, gold:3600,  exp:2600},
  {name:'格拉卡',     monster:'boss',   mname:'牛头王 萨乌塔',lv:22,rounds:20, hp:900, gold:9800,  exp:7200},
];
let dungeonIdx = 0;
let running = false, progress = 0, round = 0, totalGold=0, totalExp=0;
let smoke = [], sparks = [], floats = [], weapons = [], hitFx = 0;
let atkAnim = {t:0, active:false}, mHurt = 0, mDeadT = 0;
let tick = 0, speed = 1;
let D = DUNGEONS[0];

function img(arr, t, fps){ return arr[Math.floor(t/fps)%arr.length]; }

// ---------- 指针点击 ----------
const zones = {};
function zone(x,y,w,h,id){ zones[id]={x,y,w,h}; }
function inZone(px,py,z){ return px>=z.x&&px<=z.x+z.w&&py>=z.y&&py<=z.y+z.h; }
cv.addEventListener('pointerdown', e=>{
  const r=cv.getBoundingClientRect();
  const px=(e.clientX-r.left)/r.width*W, py=(e.clientY-r.top)/r.height*H;
  for(const id in zones){ if(inZone(px,py,zones[id])) handleClick(id); }
});
function handleClick(id){
  if(id.startsWith('dungeon')){ dungeonIdx=+id.split(':')[1]; selectDungeon(); }
  else if(id==='start'){ toggleStart(); }
  else if(id==='speed'){ speed = speed===1?2:speed===2?4:1; }
}

function selectDungeon(){
  D = DUNGEONS[dungeonIdx];
  running=false; progress=0; round=0; smoke=[]; sparks=[]; floats=[]; weapons=[];
  mDeadT=0; atkAnim.active=false;
}
function toggleStart(){
  if(round>=D.rounds){ round=0; progress=0; totalGold=0; totalExp=0; }
  running=!running;
}

// ---------- 冒烟粒子 ----------
function spawnSmoke(x,y,power){
  for(let i=0;i<2;i++){
    smoke.push({x:x+(Math.random()-.5)*10, y:y+(Math.random()-.5)*4,
      vx:(Math.random()-.5)*.5, vy:-.35-Math.random()*.5,
      r:3+Math.random()*4, life:1, decay:.008+Math.random()*.008});
  }
  if(Math.random()<.5) sparks.push({x:x+(Math.random()-.5)*8,y:y,
    vx:(Math.random()-.5)*1.4, vy:-.6-Math.random()*.8, life:1, decay:.02});
}
// ---------- 刀剑粒子（进度推进时喷出） ----------
const BLADE_COLORS = ['#e8eef5','#f4d98a','#cfe3ff','#ffe6b0','#d9c7ff'];
function spawnWeapon(x,y){
  weapons.push({
    x:x+(Math.random()-.5)*30, y:y,
    vx:(Math.random()-.5)*2.6, vy:-1.6-Math.random()*1.8,
    rot:(Math.random()-.5)*1.4, vr:(Math.random()-.5)*.16,
    kind:Math.random()<.5?'sword':'blade',
    len:16+Math.random()*12,
    color:BLADE_COLORS[Math.floor(Math.random()*BLADE_COLORS.length)],
    life:1, decay:.014+Math.random()*.012
  });
}
function updateParticles(){
  for(const s of smoke){ s.x+=s.vx; s.y+=s.vy; s.vy*=.99; s.r+=.06; s.life-=s.decay; }
  smoke=smoke.filter(s=>s.life>0);
  for(const s of sparks){ s.x+=s.vx; s.y+=s.vy; s.vy+=.02; s.life-=s.decay; }
  sparks=sparks.filter(s=>s.life>0);
  for(const w of weapons){ w.x+=w.vx; w.y+=w.vy; w.vy+=.03; w.rot+=w.vr; w.life-=w.decay; }
  weapons=weapons.filter(w=>w.life>0);
  for(const f of floats){ f.y-=.6; f.life--; }
  floats=floats.filter(f=>f.life>0);
}
// 画一把剑（竖直，剑尖朝上）
function drawSword(len){
  ctx.beginPath();
  ctx.moveTo(0,-len);
  ctx.lineTo(2.2,-len*0.55);
  ctx.lineTo(2.2,len*0.35);
  ctx.lineTo(-2.2,len*0.35);
  ctx.lineTo(-2.2,-len*0.55);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(-len*0.22,len*0.35,len*0.44,3.2);       // 护手
  ctx.fillRect(-1.8,len*0.35+3,3.6,len*0.28);           // 剑柄
}
// 画一把刀（带弧度的刀身）
function drawBlade(len){
  ctx.beginPath();
  ctx.moveTo(-len*0.1,-len);
  ctx.quadraticCurveTo(len*0.45,-len*0.3, len*0.18,len*0.4);
  ctx.lineTo(len*0.02,len*0.4);
  ctx.quadraticCurveTo(len*0.28,-len*0.3, -len*0.18,-len);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(-len*0.2,len*0.4,len*0.42,3.2);          // 护手
  ctx.fillRect(-1.6,len*0.4+3,3.2,len*0.26);            // 刀柄
}
function drawWeapons(){
  for(const w of weapons){
    ctx.save();
    ctx.globalAlpha=Math.min(1,w.life*1.8);
    ctx.translate(w.x,w.y);
    ctx.rotate(w.rot);
    ctx.fillStyle=w.color;
    ctx.shadowColor=w.color; ctx.shadowBlur=8;
    if(w.kind==='sword') drawSword(w.len); else drawBlade(w.len);
    ctx.restore();
  }
  ctx.shadowBlur=0;
}

// ---------- 战斗动画 ----------
function updateBattle(){
  tick++;
  if(atkAnim.active){ atkAnim.t++; if(atkAnim.t>26){ atkAnim.active=false; atkAnim.t=0; } }
  if(mHurt>0) mHurt--;
  if(mDeadT>0){ mDeadT--; if(mDeadT===0){ /* 怪物复活，下一只 */ } }
  if(running && !atkAnim.active && mDeadT<=0 && tick%42===0){
    atkAnim.active=true; atkAnim.t=0;
  }
  if(atkAnim.active && atkAnim.t===13){
    mHurt=14; hitFx=8;
    floats.push({x:690,y:300,text:'伤害 '+(D.hp+Math.floor(Math.random()*90)),life:60});
  }
  if(hitFx>0) hitFx--;
}

// ---------- 扫荡逻辑 ----------
function updateSweep(){
  if(!running) return;
  progress += (0.42 + speed*0.55);   // 速度影响进度
  // 进度推进时喷出刀剑：速度档位越高越密
  const bx=170, by=548, bw=660;
  const emitX=bx+2+(bw-4)*progress/100, emitY=by+8;
  const count = speed===1?1 : speed===2?2 : 4;
  for(let i=0;i<count;i++){
    if(Math.random()<(speed===4?0.9:0.55)) spawnWeapon(emitX,emitY);
  }
  if(progress>=100){
    progress=0; round++;
    const g=D.gold+Math.floor(Math.random()*400), e=D.exp+Math.floor(Math.random()*300);
    totalGold+=g; totalExp+=e;
    floats.push({x:500,y:180,text:'第 '+round+' 轮完成  +'+g+' 金币  +'+e+' 经验',life:100,big:true});
    mDeadT=30;
    if(round>=D.rounds){ running=false; progress=100; }
  }
}

function update(){ updateBattle(); updateSweep(); updateParticles(); }

// ---------- 绘制 ----------
function roundRect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r);
  ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }

function drawBackground(){
  if(bgImg.complete){
    const bw=Math.max(W,bgImg.width), bh=Math.max(H-150,bgImg.height);
    ctx.drawImage(bgImg,-(bw-W)/2,150-(bh-(H-150)),bw,bh);
  } else { ctx.fillStyle='#3a3428'; ctx.fillRect(0,150,W,H-150); }
  ctx.fillStyle='rgba(0,0,0,.25)'; ctx.fillRect(0,470,W,H-470);
}

function drawActor(key,x,baseY,hurt,atk){
  const state = key==='player' ? (atk?'attack':'idle') : (hurt?'hurt':'idle');
  const arr = SPR[key][state] || SPR[key].idle;
  const t = key==='player' ? (atk?atkAnim.t:tick) : tick;
  const im = img(arr, key==='player'&&atk?atkAnim.t:tick, key==='player'?3:4);
  if(!im.complete) return;
  ctx.save();
  const sc = key==='boss'?1.35:1.15;
  ctx.translate(x+(hurt?(Math.random()-.5)*6:0), baseY);
  if(key!=='player') ctx.scale(-1,1);
  ctx.drawImage(im,-im.width*sc/2,-im.height*sc,im.width*sc,im.height*sc);
  ctx.restore();
}

function drawBattleScene(){
  drawBackground();
  drawActor('player', 330, 470, false, atkAnim.active);
  if(mDeadT<=0) drawActor(D.monster, 700, 470, mHurt>0, false);
  if(hitFx>0){
    ctx.save(); ctx.globalAlpha=hitFx/8;
    ctx.fillStyle='#fff'; ctx.font='bold 40px sans-serif'; ctx.fillText('斩!',640,330);
    ctx.restore();
  }
  // 战斗标题
  ctx.fillStyle='rgba(0,0,0,.45)'; roundRect(20,170,300,54,6); ctx.fill();
  ctx.fillStyle='#f4d9a0'; ctx.font='bold 18px sans-serif';
  ctx.fillText(D.name,34,196);
  ctx.fillStyle='#b9b3a6'; ctx.font='12px sans-serif';
  ctx.fillText('推荐 Lv.'+D.lv+'  ·  自动战斗中',34,215);
  // 怪物血条
  ctx.fillStyle='rgba(0,0,0,.6)'; ctx.fillRect(630,150,340,12);
  ctx.fillStyle='#c0392b'; ctx.fillRect(630,150,340*(mHurt>0?0.35:0.85),12);
  ctx.fillStyle='#fff'; ctx.font='12px sans-serif'; ctx.fillText(D.mname,630,144);
}

// ---------- 冒烟进度条 ----------
function drawSmokeBar(){
  const bx=170, by=548, bw=660, bh=30;
  // 标题与轮次
  ctx.fillStyle='#f4d9a0'; ctx.font='bold 15px sans-serif';
  ctx.fillText('扫荡进度',bx,by-12);
  ctx.textAlign='right'; ctx.fillStyle='#d8a44b';
  ctx.fillText('第 '+Math.min(round+1,D.rounds)+' / '+D.rounds+' 轮',bx+bw,by-12);
  ctx.textAlign='left';
  // 外框
  ctx.fillStyle='#14161b'; roundRect(bx,by,bw,bh,8); ctx.fill();
  ctx.strokeStyle='#4a3a22'; ctx.lineWidth=2; roundRect(bx,by,bw,bh,8); ctx.stroke();
  // 轨道纹理
  for(let i=1;i<20;i++){ ctx.fillStyle='rgba(255,255,255,.04)'; ctx.fillRect(bx+i*bw/20,by+2,1,bh-4); }
  // 填充
  const fw=(bw-4)*progress/100;
  if(fw>2){
    const g=ctx.createLinearGradient(bx,0,bx+fw,0);
    g.addColorStop(0,'#b8731f'); g.addColorStop(.7,'#e8a93c'); g.addColorStop(1,'#ffd87a');
    ctx.save(); roundRect(bx+2,by+2,fw,bh-4,6); ctx.clip();
    ctx.fillStyle=g; ctx.fillRect(bx+2,by+2,fw,bh-4);
    // 高光
    ctx.fillStyle='rgba(255,255,255,.18)'; ctx.fillRect(bx+2,by+4,fw,5);
    ctx.restore();
    // 进度端点 + 冒烟源
    const hx=bx+2+fw;
    ctx.fillStyle='#fff6d8'; ctx.beginPath(); ctx.arc(hx,by+bh/2,5,0,7); ctx.fill();
    if(running && progress<100){
      for(let i=0;i<2;i++) spawnSmoke(hx, by+bh/2-2, 1);
      ctx.save(); ctx.globalAlpha=.5; ctx.fillStyle='#ff8a3c';
      ctx.beginPath(); ctx.arc(hx,by+bh/2,9+Math.sin(tick*.4)*2,0,7); ctx.fill(); ctx.restore();
    }
  }
  // 百分比
  ctx.fillStyle='#fff'; ctx.font='bold 14px sans-serif'; ctx.textAlign='center';
  ctx.fillText(Math.floor(progress)+'%', bx+bw/2, by+bh/2+5);
  ctx.textAlign='left';
  // 冒烟粒子（灰白蒸汽）
  for(const s of smoke){
    ctx.globalAlpha=s.life*.4;
    const rg=ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r);
    rg.addColorStop(0,'#e8e4dc'); rg.addColorStop(1,'rgba(200,195,185,0)');
    ctx.fillStyle=rg; ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,7); ctx.fill();
  }
  ctx.globalAlpha=1;
  for(const s of sparks){ ctx.globalAlpha=s.life; ctx.fillStyle='#ffb347';
    ctx.fillRect(s.x,s.y,2,2); }
  ctx.globalAlpha=1;
  drawWeapons();
}

// ---------- 顶部栏 / 副本选择 / 按钮 ----------
function drawTopBar(){
  ctx.fillStyle='#101318'; ctx.fillRect(0,0,W,84);
  ctx.fillStyle='#2a2f38'; ctx.fillRect(0,83,W,2);
  ctx.fillStyle='#ffd98a'; ctx.font='bold 24px sans-serif';
  ctx.fillText('地下城与勇士 · 扫荡挂机',24,38);
  ctx.fillStyle='#8f8a80'; ctx.font='12px sans-serif';
  ctx.fillText('真实客户端素材 · 自动扫荡 · 加速时刀剑喷发',24,60);
  // 收益
  ctx.textAlign='right';
  ctx.fillStyle='#e8c46a'; ctx.font='bold 16px sans-serif';
  ctx.fillText('金币 '+totalGold.toLocaleString()+'    经验 '+totalExp.toLocaleString(),W-24,38);
  ctx.fillStyle='#7f8a7a'; ctx.font='12px sans-serif';
  ctx.fillText('速度 x'+speed+'  ·  已完成 '+round+' 轮',W-24,60);
  ctx.textAlign='left';
}
function drawDungeonList(){
  ctx.fillStyle='#0f1116'; ctx.fillRect(0,84,230,H-84);
  ctx.fillStyle='#2a2f38'; ctx.fillRect(229,84,2,H-84);
  ctx.fillStyle='#b9b3a6'; ctx.font='bold 14px sans-serif'; ctx.fillText('选择副本',20,116);
  const y0=136, ih=78;
  DUNGEONS.forEach((d,i)=>{
    const y=y0+i*ih, sel=i===dungeonIdx;
    ctx.fillStyle=sel?'#2a2418':'#171a20'; roundRect(14,y,202,66,8); ctx.fill();
    if(sel){ ctx.strokeStyle='#d8a44b'; ctx.lineWidth=2; roundRect(14,y,202,66,8); ctx.stroke(); }
    ctx.fillStyle=sel?'#ffd98a':'#cfc9bc'; ctx.font='bold 15px sans-serif';
    ctx.fillText(d.name,28,y+27);
    ctx.fillStyle='#8f8a80'; ctx.font='12px sans-serif';
    ctx.fillText('Lv.'+d.lv+' · '+d.mname,28,y+48);
    zone('dungeon:'+i,14,y,202,66);
  });
}
function drawControls(){
  const by=592;
  // 开始/暂停
  const sx=860, sw=120, sy=540;
  ctx.fillStyle=running?'#5a2c1a':'#2f6b3a'; roundRect(sx,sy,sw,42,8); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 16px sans-serif'; ctx.textAlign='center';
  ctx.fillText(running?'暂停扫荡':(round>=D.rounds?'再次扫荡':'开始扫荡'),sx+sw/2,sy+27);
  zone('start',sx,sy,sw,42);
  // 加速
  ctx.fillStyle='#2a3546'; roundRect(sx,sy+52,sw,34,8); ctx.fill();
  ctx.fillStyle='#cfe0ff'; ctx.font='bold 14px sans-serif';
  ctx.fillText('速度 x'+speed,sx+sw/2,sy+74);
  zone('speed',sx,sy+52,sw,34);
  ctx.textAlign='left';
}

function drawFloats(){
  for(const f of floats){
    ctx.globalAlpha=Math.min(1,f.life/30);
    ctx.fillStyle=f.big?'#ffd98a':'#ffe08a';
    ctx.font=(f.big?'bold 22px':'bold 18px')+' sans-serif';
    ctx.textAlign='center'; ctx.fillText(f.text, f.big?W/2:f.x, f.y);
    ctx.textAlign='left';
  }
  ctx.globalAlpha=1;
}

function render(){
  ctx.clearRect(0,0,W,H);
  drawBattleScene();
  drawSmokeBar();
  drawTopBar();
  drawDungeonList();
  drawControls();
  drawFloats();
}
function loop(){ update(); render(); requestAnimationFrame(loop); }
selectDungeon(); loop();
</script>
</body>
</html>
"""

html = HTML.replace("__SPRITES_JSON__", json.dumps(sprites)).replace("__BG_DATA__", json.dumps(bg))
out = os.path.join(ROOT, "dist", "dnf-sweep-idle.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("Built:", out, "|", os.path.getsize(out) // 1024, "KB")
