"""
DNF 像素格斗 H5 · 构建脚本
把所有 PNG 素材以 base64 内联进单文件 HTML，产物可直接双击打开 / iframe 嵌入。

用法：  python scripts/build.py
产物：  dist/dnf-pixel-battle.html
依赖：  仅 Python 3 标准库
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
        "skill":  frames("player", list(range(30, 40))),
        "hurt":   frames("player", list(range(120, 126))),
    },
    "goblin": {
        "idle":   frames("goblin", list(range(10, 16))),
        "attack": frames("goblin", list(range(0, 6))),
        "hurt":   frames("goblin", [8, 9]),
    },
    "boss": {
        "idle":   frames("boss", list(range(21, 32))),
        "attack": frames("boss", list(range(0, 8))),
        "hurt":   frames("boss", list(range(16, 20))),
    },
}
bg = data_url(os.path.join(ASSETS, "bg.png"))

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>DNF 像素格斗 · 真实素材 H5 Demo</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { margin:0; height:100%; background:#0d0f12; overflow:hidden; font-family:"Microsoft YaHei",sans-serif; }
  #wrap { position:relative; width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
  canvas { display:block; width:100%; height:100%; object-fit:contain; background:#000; }
  #ui { position:absolute; inset:0; pointer-events:none; }
  #title { position:absolute; left:18px; top:14px; color:#f4d9a0; font-size:15px; letter-spacing:1px; text-shadow:0 2px 4px #000; }
  #hint { position:absolute; left:18px; top:38px; color:#b9b3a6; font-size:12px; text-shadow:0 1px 3px #000; }
  #pad { position:absolute; left:0; right:0; bottom:14px; display:flex; justify-content:center; gap:12px; pointer-events:auto; }
  .btn { width:58px; height:58px; border-radius:50%; border:1px solid rgba(255,225,160,.35); background:rgba(20,20,24,.55);
         color:#f4d9a0; font-size:16px; font-weight:700; display:flex; align-items:center; justify-content:center;
         user-select:none; touch-action:none; backdrop-filter:blur(3px); }
  .btn:active { background:rgba(180,130,60,.6); transform:scale(.94); }
  #overlay { position:absolute; inset:0; display:none; align-items:center; justify-content:center; flex-direction:column;
             background:rgba(0,0,0,.62); pointer-events:auto; }
  #overlay h1 { color:#ffd98a; font-size:34px; margin:0 0 12px; text-shadow:0 3px 0 #5a2c00; }
  #overlay p { color:#ddd; margin:4px 0; font-size:14px; }
  #restart { margin-top:20px; padding:10px 30px; border:1px solid #d8a44b; background:#2a2013; color:#ffd98a;
             font-size:16px; cursor:pointer; border-radius:4px; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="game" width="960" height="540"></canvas>
  <div id="ui">
    <div id="title">地下城与勇士 · 像素格斗 H5</div>
    <div id="hint">A/D 或 ←/→ 移动 · X 攻击 · Z 技能 · C 跳跃 · 手机点下方按钮</div>
    <div id="pad">
      <div class="btn" data-key="left">◀</div>
      <div class="btn" data-key="right">▶</div>
      <div class="btn" data-key="attack">X</div>
      <div class="btn" data-key="skill">Z</div>
      <div class="btn" data-key="jump">↑</div>
    </div>
    <div id="overlay">
      <h1 id="result">胜利</h1>
      <p id="sub"></p>
      <button id="restart">再战一次</button>
    </div>
  </div>
</div>
<script>
const SPR = __SPRITES_JSON__;
const BG = __BG_DATA__;
const cv = document.getElementById('game');
const ctx = cv.getContext('2d');
const W = cv.width, H = cv.height, GROUND = 430;

function load(src){ const i = new Image(); i.src = src; return i; }
for (const k in SPR) for (const a in SPR[k]) SPR[k][a] = SPR[k][a].map(load);
const bgImg = load(BG);

const keys = {};
document.addEventListener('keydown', e => { keys[e.key.toLowerCase()] = true; });
document.addEventListener('keyup', e => { keys[e.key.toLowerCase()] = false; });
document.querySelectorAll('.btn').forEach(b => {
  const k = b.dataset.key;
  const on = e => { e.preventDefault(); keys[k] = true; };
  const off = e => { e.preventDefault(); keys[k] = false; };
  b.addEventListener('pointerdown', on); b.addEventListener('pointerup', off);
  b.addEventListener('pointerleave', off); b.addEventListener('pointercancel', off);
});

function makeActor(kind, x, hp, dmg, speed){
  return {kind,x,y:GROUND,hp,maxHp:hp,dmg,speed,state:'idle',frame:0,frameTime:0,
          facing:kind==='player'?1:-1,vy:0,onGround:true,hitTimer:0,attackDone:false,
          cooldown:0,stun:0};
}
let player, enemy, stage, floaters, shake, combo, comboTimer, gameOver;

function reset(){
  player = makeActor('player',210,240,14,3.4);
  enemy = makeActor('goblin',720,180,8,1.5);
  stage = 0; floaters=[]; shake=0; combo=0; comboTimer=0; gameOver=false;
  document.getElementById('overlay').style.display='none';
}
reset();
document.getElementById('restart').onclick = reset;

function setState(a,s){ if(a.state!==s){ a.state=s; a.frame=0; a.frameTime=0; a.attackDone=false; } }
function imgOf(a){ const arr = SPR[a.kind][a.state] || SPR[a.kind].idle; return arr[Math.min(a.frame, arr.length-1)]; }
function act(a){
  if(a.hitTimer>0) a.hitTimer--;
  if(a.stun>0){ a.stun--; setState(a,'hurt'); return; }
  if(a.cooldown>0) a.cooldown--;
  if(a.state==='attack'||a.state==='skill'||a.state==='hurt'){
    a.frameTime++;
    const len = SPR[a.kind][a.state].length;
    if(a.frameTime >= 4){ a.frameTime=0; a.frame++; }
    if(a.frame>=len){ setState(a,'idle'); return; }
    if((a.state==='attack'||a.state==='skill') && a.frame===3 && !a.attackDone){
      a.attackDone=true;
      doHit(a);
    }
    return;
  }
  setState(a,'idle');
}

function doHit(a){
  const range = a.state==='skill'?175:105;
  const target = a.kind==='player' ? enemy : player;
  const dx = target.x - a.x;
  if(a.kind==='player'){
    if(Math.abs(dx)<range && (dx>0)===(a.facing>0)){
      const dmg = (a.state==='skill'?38:14) + Math.floor(Math.random()*8);
      enemy.hp -= dmg; enemy.stun=12; enemy.x += a.facing*16;
      floaters.push({x:enemy.x, y:enemy.y-120, text:'-'+dmg, color:'#ffe08a', life:60});
      combo++; comboTimer=90; shake=6;
      if(enemy.hp<=0) killEnemy();
    }
  } else {
    if(Math.abs(dx)<90 && (dx>0)===(a.facing>0) && player.hitTimer<=0){
      const dmg = a.dmg + Math.floor(Math.random()*5);
      player.hp -= dmg; player.stun=10; player.hitTimer=20; player.x += a.facing*12;
      floaters.push({x:player.x, y:player.y-130, text:'-'+dmg, color:'#ff8080', life:60});
      shake=4;
      if(player.hp<=0) finish(false);
    }
  }
}

function killEnemy(){
  if(stage===0){
    stage=1;
    enemy = makeActor('boss',760,520,15,1.15);
    floaters.push({x:700,y:180,text:'牛头王 萨乌塔 出现!',color:'#ff9d5c',life:140});
    shake=14;
  } else {
    finish(true);
  }
}
function finish(win){
  gameOver=true;
  document.getElementById('result').textContent = win?'通关！':'挑战失败';
  document.getElementById('sub').textContent = win?'你击败了所有怪物 · 素材来自 DNF 客户端解包':'再练练手，勇士';
  document.getElementById('overlay').style.display='flex';
}

let tick=0;
function update(){
  if(gameOver) return;
  tick++;
  const left = keys['a']||keys['arrowleft']||keys['left'];
  const right = keys['d']||keys['arrowright']||keys['right'];
  if(player.stun<=0){
    if(left){ player.x-=player.speed; player.facing=-1; }
    if(right){ player.x+=player.speed; player.facing=1; }
    if(keys['x']||keys['attack']){ if(player.state==='idle'&&player.cooldown<=0){ setState(player,'attack'); player.cooldown=16; } }
    if(keys['z']||keys['skill']){ if(player.state==='idle'&&player.cooldown<=0){ setState(player,'skill'); player.cooldown=110; } }
    if(keys['c']||keys['w']||keys['arrowup']||keys['jump']){ if(player.onGround){ player.vy=-14; player.onGround=false; } }
  }
  player.x = Math.max(40, Math.min(W-40, player.x));
  if(!player.onGround){ player.y += player.vy; player.vy += 0.9; if(player.y>=GROUND){ player.y=GROUND; player.onGround=true; } }
  act(player);

  if(enemy.stun<=0){
    const d = player.x - enemy.x;
    if(Math.abs(d)>95){ enemy.x += Math.sign(d)*enemy.speed; enemy.facing = Math.sign(d)||enemy.facing; }
    else if(enemy.state==='idle' && enemy.cooldown<=0){ setState(enemy,'attack'); enemy.cooldown=80; }
  }
  act(enemy);

  floaters.forEach(f=>{ f.y-=1.1; f.life--; });
  floaters = floaters.filter(f=>f.life>0);
  if(comboTimer>0){ comboTimer--; if(comboTimer===0) combo=0; }
  if(shake>0) shake--;
}
function drawBar(x,y,w,h,pct,color,label){
  ctx.fillStyle='rgba(0,0,0,.7)'; ctx.fillRect(x-2,y-2,w+4,h+4);
  ctx.fillStyle='#3a2020'; ctx.fillRect(x,y,w,h);
  ctx.fillStyle=color; ctx.fillRect(x,y,w*Math.max(0,pct),h);
  ctx.fillStyle='#fff'; ctx.font='12px sans-serif'; ctx.fillText(label,x,y-7);
}
function drawActor(a){
  const img = imgOf(a);
  if(!img.complete) return;
  ctx.save();
  ctx.translate(a.x + (Math.random()-.5)*(shake?2:0), a.y + (Math.random()-.5)*(shake?2:0));
  if(a.facing<0) ctx.scale(-1,1);
  const scale = a.kind==='boss'?1.12:1;
  ctx.drawImage(img, -img.width*scale/2, -img.height*scale, img.width*scale, img.height*scale);
  if(a.hitTimer>0){ ctx.globalCompositeOperation='lighter'; ctx.globalAlpha=.25; ctx.drawImage(img,-img.width*scale/2,-img.height*scale,img.width*scale,img.height*scale); }
  ctx.restore();
}
function render(){
  ctx.save();
  ctx.clearRect(0,0,W,H);
  if(bgImg.complete){
    const bw=Math.max(W,bgImg.width), bh=Math.max(H,bgImg.height);
    ctx.drawImage(bgImg, -(bw-W)/2 - player.x*.05, H-bh, bw, bh);
  } else { ctx.fillStyle='#3a3428'; ctx.fillRect(0,0,W,H); }
  ctx.fillStyle='rgba(0,0,0,.28)'; ctx.fillRect(0,GROUND,W,H-GROUND);
  ctx.fillStyle='#6b5b3e'; ctx.fillRect(0,GROUND,W,3);

  drawActor(player); drawActor(enemy);

  drawBar(40,26,320,16,player.hp/player.maxHp,'#4caf50','鬼剑士  Lv.60');
  drawBar(600,26,320,16,enemy.hp/enemy.maxHp,stage===0?'#d4b142':'#c0392b',stage===0?'哥布林':'牛头王 萨乌塔');
  ctx.fillStyle='#ffd98a'; ctx.font='14px sans-serif';
  ctx.fillText('技能 Z  '+(player.cooldown>0?(player.cooldown/60).toFixed(1)+'s':'READY'),40,64);
  if(combo>0){ ctx.fillStyle='#ffb347'; ctx.font='bold 28px sans-serif'; ctx.fillText(combo+' COMBO',W/2-60,90); }
  floaters.forEach(f=>{ ctx.fillStyle=f.color; ctx.font='bold 20px sans-serif'; ctx.globalAlpha=Math.min(1,f.life/30); ctx.fillText(f.text,f.x-20,f.y); ctx.globalAlpha=1; });
  ctx.restore();
}
function loop(){ update(); render(); requestAnimationFrame(loop); }
loop();
</script>
</body>
</html>
"""

html = HTML.replace("__SPRITES_JSON__", json.dumps(sprites)).replace("__BG_DATA__", json.dumps(bg))
out_dir = os.path.join(ROOT, "dist")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "dnf-pixel-battle.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("Built:", out, "|", os.path.getsize(out) // 1024, "KB")
