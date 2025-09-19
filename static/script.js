// Interactive UI — now supports real Twitter data via backend API

const simulateBtn = document.getElementById('simulateBtn');
const clearBtn = document.getElementById('clearBtn');
const exportBtn = document.getElementById('exportBtn');
const tipsBtn = document.getElementById('tipsBtn');

const alertEl = document.getElementById('alertValue');
const indicator = document.getElementById('indicator');
const negCount = document.getElementById('negCount');
const neuCount = document.getElementById('neuCount');
const posCount = document.getElementById('posCount');
const feedEl = document.getElementById('feed');

// Chart setup
const trendCtx = document.getElementById('trendChart').getContext('2d');
const sentCtx = document.getElementById('sentChart').getContext('2d');

const trendChart = new Chart(trendCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Alert score', data: [], tension: 0.3, fill: true }]},
  options: { scales: { y: { beginAtZero: true, max: 100 } }, plugins:{legend:{display:false}} }
});
const sentChart = new Chart(sentCtx, {
  type: 'doughnut',
  data: { labels: ['Negative','Neutral','Positive'], datasets: [{ data: [0,0,0], backgroundColor: ['#ff6b6b','#6b7b8f','#2bd4a7'] }]},
  options: { plugins:{legend:{position:'bottom',labels:{color:'#e6eef6'}}} }
});

// Map init
const map = L.map('map',{zoomControl:false}).setView([20.6,78.9],4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:''}).addTo(map);
let markers = [];
function clearMarkers(){ markers.forEach(m=>map.removeLayer(m)); markers=[]; }

// Demo generator
function randomBetween(min,max){ return Math.random()*(max-min)+min; }
function randomLatLonIn(region){
  if(region==='india') return [randomBetween(8,28), randomBetween(68,97)];
  if(region==='usa') return [randomBetween(25,49), randomBetween(-125,-67)];
  return [randomBetween(-30,55), randomBetween(-130,150)];
}

function generateDemoPosts(n=8, keyword='#flood', region='any'){
  const types = ['Flood','Wildfire','Landslide','Cyclone','Earthquake','Drought'];
  const posts = [];
  for(let i=0;i<n;i++){
    const type = types[Math.floor(Math.random()*types.length)];
    const latlon = randomLatLonIn(region);
    const severity = +(Math.min(4, Math.random()*3 + (type==='Earthquake'?1.2:0))).toFixed(2);
    const text = `${keyword} ${type} reported — severity:${Math.round(severity*25)}%`;
    posts.push({text, lat:latlon[0], lon:latlon[1], timestamp: Date.now() - i*60000, severity});
  }
  return posts;
}

function updateIndicator(value){
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const dash = 100 - pct;
  indicator.style.strokeDashoffset = dash;
  alertEl.textContent = pct + '%';
}

// Render posts into feed and charts
function render(posts){
  let neg=0,neu=0,pos=0,scoreSum=0;
  feedEl.innerHTML = '';
  posts.forEach(p=>{
    const d = document.createElement('div'); d.className='post';
    const left = document.createElement('div'); left.className='left-ind';
    const color = p.severity>2 ? '#ff6b6b' : (p.severity>1 ? '#ff9f1c' : '#2bd4a7');
    left.style.background = color;
    const body = document.createElement('div'); body.style.flex=1;
    body.innerHTML = `<div style="font-weight:700">${p.text}</div><div style="font-size:12px;color:#9aa6b2">${new Date(p.timestamp).toLocaleString()}</div>`;
    d.appendChild(left); d.appendChild(body); feedEl.appendChild(d);

    if(p.severity>1.5) neg++; else if(p.severity>0.5) neu++; else pos++;
    scoreSum += p.severity*20;
  });

  negCount.textContent = neg;
  neuCount.textContent = neu;
  posCount.textContent = pos;

  const avgScore = posts.length ? Math.round(scoreSum / posts.length) : 0;
  updateIndicator(avgScore);

  const timeLabel = new Date().toLocaleTimeString();
  trendChart.data.labels.push(timeLabel);
  trendChart.data.datasets[0].data.push(avgScore);
  if(trendChart.data.labels.length > 12){ trendChart.data.labels.shift(); trendChart.data.datasets[0].data.shift(); }
  trendChart.update();

  sentChart.data.datasets[0].data = [neg, neu, pos];
  sentChart.update();

  clearMarkers();
  posts.forEach(p=>{
    const color = p.severity>2 ? '#ff6b6b' : (p.severity>1 ? '#ff9f1c' : '#2bd4a7');
    const c = L.circleMarker([p.lat,p.lon],{radius:8,fillColor:color,color:'#000',weight:0.6,fillOpacity:0.95}).addTo(map);
    c.bindPopup(`<b>${p.text}</b><br>${new Date(p.timestamp).toLocaleString()}`);
    markers.push(c);
  });
  if(markers.length) map.setView([posts[0].lat, posts[0].lon],5);
}

// Simulation control
let autoTimer = null;
simulateBtn.addEventListener('click', async ()=>{
  const k = document.getElementById('keyword').value || '#flood';
  const r = document.getElementById('region').value || 'any';
  const useReal = confirm("Real Twitter data fetch karna hai? OK for real, Cancel for demo.");
  let result;
  if(useReal){
    result = await analyzeWithAPI([], k, r, true);
    console.log("Backend Response:", result);
    render(result.posts);
    updateIndicator(result.score);
    negCount.textContent = result.neg;
    neuCount.textContent = result.neu;
    posCount.textContent = result.pos;
    // periodic animation band rahegi real data ke liye
    if(autoTimer) clearInterval(autoTimer);
  }else{
    const posts = generateDemoPosts(9, k, r);
    render(posts);
    if(autoTimer) clearInterval(autoTimer);
    autoTimer = setInterval(()=>{
      const posts2 = generateDemoPosts(6, k, r);
      render(posts2);
    }, 3500);
  }
});

clearBtn.addEventListener('click', ()=>{
  if(autoTimer) clearInterval(autoTimer);
  updateIndicator(0);
  negCount.textContent = neuCount.textContent = posCount.textContent = 0;
  feedEl.innerHTML = '';
  clearMarkers();
  trendChart.data.labels = []; trendChart.data.datasets[0].data = []; trendChart.update();
  sentChart.data.datasets[0].data = [0,0,0]; sentChart.update();
});

exportBtn.addEventListener('click', ()=>{
  const posts = Array.from(feedEl.querySelectorAll('.post')).map(p => ({
    text: p.querySelector('div[style*="font-weight"]').innerText,
    time: p.querySelector('div[style*="font-size"]').innerText
  }));

  const blob = new Blob([JSON.stringify(posts, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = 'posts.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
});
tipsBtn.addEventListener('click', ()=>{
  alert('Training tips:\n1) Label 2-5k tweets across classes.\n2) Fine-tune DistilBERT for classification.\n3) Predict severity via regression head.');
});

document.addEventListener('DOMContentLoaded', ()=> {
  updateIndicator(0);
});

// API call function, now supports real data
async function analyzeWithAPI(posts=[], keyword="#flood", region="any", real=false) {
  const res = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ posts, keyword, region, real })
  });
  const data = await res.json();
  return data;
}