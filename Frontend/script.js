(function(){
  var $=function(id){return document.getElementById(id);};
  if(window.matchMedia('(prefers-reduced-motion:reduce)').matches)gsap.globalTimeline.timeScale(100);

  // count-up helper
  function count(el,to,suf,dur){
    var o={v:0};suf=suf||'';
    gsap.to(o,{v:to,duration:dur||1.2,ease:'power2.out',onUpdate:function(){el.textContent=Math.round(o.v)+suf;}});
  }

  var cap=function(x){return x.charAt(0).toUpperCase()+x.slice(1);};
  function get(u){return fetch('/api'+u).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();});}

  /* ---------- HOME ---------- */
  var d={occ:0,wait:0,arr:0,staff:0};
  function set(id,text,cls,label){
    $('v-'+id).textContent=text;
    $('s-'+id).textContent=label||cap(cls);
    $('k-'+id).className='kpi c-'+cls;
  }
  function loadHome(k){
    d={occ:k.occupancy.value,wait:k.wait.value,arr:k.arrivals.value,staff:k.staff.value};
    set('occ',d.occ+'%',k.occupancy.level);
    set('wait',d.wait+' min',k.wait.level);
    set('arr',d.arr,k.arrivals.level,k.arrivals.level==='green'?'Normal':'High');
    set('staff',d.staff+'%',k.staff.level);
    $('asof').textContent='Data as of '+k.as_of.replace('T',' ').slice(0,16)+' (synthetic dataset)';
  }
  $('goStatus').onclick=function(){gsap.to(window,{scrollTo:0,duration:0});$('status').scrollIntoView({behavior:'smooth'});gsap.fromTo('#home .kpi',{scale:1.06},{scale:1,duration:.6,stagger:.08,ease:'back.out(3)'});};

  /* ---------- TRENDS ---------- */
  var M={},cur='arrivals',svg=$('svg'),NS='http://www.w3.org/2000/svg',L=70,R=950,T=40,B=270;
  function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t)e.textContent=t;svg.appendChild(e);return e;}
  function draw(){
    var m=M[cur];if(!m)return;
    var n=Math.min(+$('range').value,m.past.length);
    var past=m.past.slice(m.past.length-n),off=m.past.length-n;
    var an=m.an.map(function(i){return i-off;}).filter(function(i){return i>=0;});
    var fc=m.fc,total=past.length+fc.length;
    var all=past.concat(fc),lo=Math.min.apply(null,all),hi=Math.max.apply(null,all),pad=(hi-lo)*.15||1;
    var mn=Math.max(0,lo-pad),mx=hi+pad;
    function X(i){return L+(R-L)*i/(total-1);}
    function Y(v){return B-(B-T)*(v-mn)/(mx-mn);}
    svg.innerHTML='';
    [0,1,2].forEach(function(g){var y=T+(B-T)*g/2;el('line',{x1:L,x2:R,y1:y,y2:y,stroke:'#c3d3d2','stroke-width':2,class:'gl'});
      el('text',{x:L-8,y:y+6,'text-anchor':'end','font-size':18,fill:'#566d73',class:'gl'},Math.round(mx-(mx-mn)*g/2));});
    var nx=X(past.length-1);
    if(fc.length)el('line',{x1:nx,x2:nx,y1:20,y2:B,stroke:'#566d73','stroke-width':2,'stroke-dasharray':'4 6',class:'now'});
    el('polyline',{points:past.map(function(v,i){return X(i)+','+Y(v);}).join(' '),fill:'none',stroke:'#0b6e6e','stroke-width':5,'stroke-linejoin':'round','stroke-linecap':'round',class:'pl'});
    if(fc.length){
      var fp=[[past.length-1,past[past.length-1]]].concat(fc.map(function(v,i){return [past.length+i,v];}));
      el('polyline',{points:fp.map(function(p){return X(p[0])+','+Y(p[1]);}).join(' '),fill:'none',stroke:'#d9a400','stroke-width':5,'stroke-dasharray':'12 9','stroke-linejoin':'round','stroke-linecap':'round',class:'fl'});
    }
    an.forEach(function(i){
      var g=el('g',{class:'an'});
      var c=document.createElementNS(NS,'circle');
      c.setAttribute('cx',X(i));c.setAttribute('cy',Y(past[i]));c.setAttribute('r',11);c.setAttribute('fill','#cf3434');c.setAttribute('stroke','#fff');c.setAttribute('stroke-width',3);g.appendChild(c);
      var t=document.createElementNS(NS,'text');
      t.setAttribute('x',X(i));t.setAttribute('y',Y(past[i])-22);t.setAttribute('text-anchor','middle');t.setAttribute('font-size',24);t.setAttribute('font-weight','500');t.setAttribute('fill','#cf3434');t.textContent='Anomaly';g.appendChild(t);
    });
    var f={'font-size':24,fill:'#566d73','font-family':'IBM Plex Sans,Segoe UI,sans-serif',class:'cap'};
    el('text',Object.assign({x:L,y:318},f),'Past (database)');
    if(fc.length)el('text',Object.assign({x:R,y:318,'text-anchor':'end'},f),'Forecast (ML)');
    $('ct').textContent=m.title;
    $('s2').textContent=m.peak;
    if(fc.length)count($('s1'),fc[0],m.suf,1);else $('s1').textContent='Not available';
    count($('s3'),an.length,'',.8);
    var p=svg.querySelector('.pl'),len=p.getTotalLength();
    var tl=gsap.timeline();
    tl.from('#svg .gl',{opacity:0,duration:.5,stagger:.1,ease:'power2.out'})
      .fromTo(p,{strokeDasharray:len,strokeDashoffset:len},{strokeDashoffset:0,duration:1.2,ease:'power1.inOut'},.2);
    if(fc.length)tl.from('#svg .now',{opacity:0,duration:.4},'-=.3').from('#svg .fl',{opacity:0,x:-30,duration:.8,ease:'power2.out'},'-=.2');
    tl.from('#svg .cap',{opacity:0,y:8,duration:.4,stagger:.1},'-=.6');
    if(svg.querySelector('.an'))tl.from('#svg .an',{scale:0,svgOrigin:'0 0',opacity:0,duration:.5,ease:'back.out(3)'},'-=.2');
    gsap.fromTo('#svg .an circle',{attr:{r:11}},{attr:{r:15},duration:.7,repeat:-1,yoyo:true,ease:'sine.inOut',delay:2});
  }
  function loadTrend(){
    if(M[cur]){draw();return;}
    get('/trend?metric='+cur+'&hours=48').then(function(r){M[cur]=r;draw();})
      .catch(function(){$('ct').textContent='Could not load data. Is the server running?';});
  }
  document.querySelectorAll('.tab').forEach(function(b){
    b.onclick=function(){
      document.querySelectorAll('.tab').forEach(function(x){x.setAttribute('aria-selected',x===b);});
      cur=b.dataset.m;gsap.killTweensOf('#svg .an circle');
      gsap.fromTo('#ct',{opacity:0,y:-8},{opacity:1,y:0,duration:.4});
      loadTrend();
    };
  });
  $('range').onchange=function(){gsap.killTweensOf('#svg .an circle');draw();};

  /* ---------- ALERTS ---------- */
  var list=$('alist');
  function loadAlerts(a){
    var cl=a.capacity.level,cc=['green','yellow','orange','red'][cl];
    $('capbox').className='box big c-'+cc;
    $('cap-v').textContent=cl===0?'Normal':'Level '+cl;
    $('cap-b').className='badge t-'+cc;
    $('cap-b').textContent=cl===0?'No surge plan needed':'Overcrowding plan Level '+cl;
    var al=$('actlist');al.innerHTML='';
    if(cl>0){
      var li0=document.createElement('li');li0.textContent='Triggered by: '+a.capacity.reasons.join(', ');al.appendChild(li0);
      a.capacity.actions.forEach(function(t){var li=document.createElement('li');li.textContent=t;al.appendChild(li);});
    }
    $('actbox').hidden=cl===0;
    list.innerHTML='';
    a.alerts.forEach(function(x){
      var li=document.createElement('li'),s=document.createElement('span'),ch=document.createElement('span'),b=document.createElement('span'),r=document.createElement('span');
      s.textContent=x.t;ch.className='chips';
      b.className='badge t-'+x.c+(x.src==='ML'&&x.c==='red'?' mlb':'');b.textContent=x.label||cap(x.c);
      r.className='src';r.textContent=x.src;
      ch.appendChild(b);ch.appendChild(r);li.appendChild(s);li.appendChild(ch);list.appendChild(li);
    });
    var order=['green','yellow','orange','red'],top='green';
    a.alerts.forEach(function(x){if(x.src==='Rule'&&order.indexOf(x.c)>order.indexOf(top))top=x.c;});
    $('hosp-v').textContent=cap(top);
    $('hosp-b').className='badge t-'+top;
    $('hosp').className='box big c-'+top;
  }

  /* ---------- DEPARTMENTS ---------- */
  var host=$('deps'),present=0,required=1,pct=0;
  function loadDeps(r){
    host.innerHTML='';
    r.departments.forEach(function(x){
      var c=document.createElement('article');c.className='box dep c-'+x.st;
      c.innerHTML='<div class="lbl"></div><div class="n"></div><div class="track" role="img"><i></i></div><span class="badge t-'+x.st+'"></span>';
      c.children[0].textContent=x.n;
      c.children[1].textContent=x.used+' / '+x.total+' beds';
      c.children[1].dataset.used=x.used;c.children[1].dataset.total=x.total;
      c.children[2].setAttribute('aria-label',Math.round(x.used/x.total*100)+'% of beds occupied');
      c.children[2].firstChild.style.width=(x.used/x.total*100)+'%';
      c.children[3].textContent=x.tag;
      host.appendChild(c);
    });
    present=r.staff.present;required=r.staff.required;pct=present/required*100;
    $('staff').className='box staff c-'+(pct>=95?'green':pct>=85?'yellow':pct>=70?'orange':'red');
  }

  /* ---------- KNOWLEDGE BASE ---------- */
  var docs=[]; /* filled from /api/documents */
  var SHOWN=8,expanded=false,dl=$('list'),more=$('more'),empty=$('empty'),search=$('search');
  function render(anim){
    var term=search.value.trim().toLowerCase(),searching=term.length>0;
    var rows=docs.filter(function(x){return !searching||x[0].toLowerCase().indexOf(term)>-1;});
    if(!searching&&!expanded)rows=rows.slice(0,SHOWN);
    dl.innerHTML='';
    rows.forEach(function(x){
      var li=document.createElement('li'),s=document.createElement('span'),a=document.createElement('a');
      s.textContent=x[0];a.textContent='View PDF';a.href='docs/'+x[1];a.target='_blank';a.rel='noopener';
      a.setAttribute('aria-label','View PDF: '+x[0]);
      li.appendChild(s);li.appendChild(a);dl.appendChild(li);
    });
    empty.hidden=rows.length>0;
    more.hidden=searching||docs.length<=SHOWN;
    more.textContent=expanded?'Show less':'+ '+(docs.length-SHOWN)+' more';
    if(anim!==false){
      gsap.from('#list li',{opacity:0,x:-24,duration:.4,stagger:.04,ease:'power2.out'});
      if(!empty.hidden)gsap.from(empty,{opacity:0,y:10,duration:.4});
    }
  }
  more.onclick=function(){expanded=!expanded;render();};
  search.oninput=render;
  function loadDocs(r){docs=r;render(false);}

  /* ---------- PER-VIEW ENTRANCE ANIMATIONS ---------- */
  var enter={
    home:function(){
      var tl=gsap.timeline({defaults:{ease:'power3.out'}});
      var h=$('h1');h.innerHTML=h.textContent.split('').map(function(c){return '<span style="display:inline-block">'+(c===' '?'&nbsp;':c)+'</span>';}).join('');
      tl.from('#h1 span',{yPercent:110,opacity:0,rotate:6,duration:.7,stagger:.04})
        .from('#home .sub',{opacity:0,x:-30,duration:.6},'-=.3')
        .from('#home .pts li',{opacity:0,y:30,duration:.6,stagger:.15},'-=.2')
        .from('#home .pts svg',{scale:0,rotate:-90,duration:.6,stagger:.15,ease:'back.out(2.5)'},'<')
        .from('#goStatus',{opacity:0,scale:.8,duration:.5,ease:'back.out(3)'},'-=.2')
        .from('#home .kpi',{opacity:0,y:50,scale:.9,duration:.7,stagger:.12},0.3)
        .from('#home .kpi .st i',{scale:0,duration:.4,stagger:.12,ease:'back.out(4)'},'-=.3');
      count($('v-occ'),d.occ,'%');count($('v-wait'),d.wait,' min');count($('v-arr'),d.arr,'');count($('v-staff'),d.staff,'%');
      gsap.to('#home .kpi .st i',{scale:1.5,opacity:.5,duration:.9,repeat:-1,yoyo:true,ease:'sine.inOut',stagger:.2,delay:1.5});
    },
    trends:function(){
      gsap.from('#trends .tab',{opacity:0,y:-20,duration:.5,stagger:.08,ease:'back.out(2)'});
      gsap.from('#range',{opacity:0,x:30,duration:.5});
      gsap.from('#trends .chart',{opacity:0,y:40,duration:.6,ease:'power3.out'});
      gsap.from('#trends .stat',{opacity:0,y:40,scale:.92,duration:.6,stagger:.12,delay:.4,ease:'power3.out'});
      gsap.killTweensOf('#svg .an circle');loadTrend();
    },
    alerts:function(){
      gsap.from('#alerts .big',{opacity:0,x:-60,duration:.7,stagger:.15,ease:'power3.out'});
      gsap.from('#alerts .big .v',{opacity:0,scale:.6,duration:.6,stagger:.15,delay:.2,ease:'back.out(2.5)'});
      gsap.from('#alerts .alerts',{opacity:0,y:40,duration:.6,delay:.3});
      gsap.from('#alist li',{opacity:0,x:-50,duration:.5,stagger:.12,delay:.5,ease:'power2.out'});
      gsap.from('#alist .badge',{scale:0,duration:.4,stagger:.12,delay:.7,ease:'back.out(3)'});
      gsap.to('#alist .mlb',{boxShadow:'0 0 0 6px rgba(207,52,52,.25)',duration:.8,repeat:-1,yoyo:true,delay:1.4});
    },
    departments:function(){
      gsap.from('#deps .dep',{opacity:0,y:50,scale:.92,duration:.6,stagger:.1,ease:'power3.out'});
      document.querySelectorAll('#deps .dep').forEach(function(c,i){
        var bar=c.querySelector('.track i'),w=bar.style.width,n=c.children[1];
        gsap.fromTo(bar,{width:0},{width:w,duration:1.1,delay:.3+i*.1,ease:'power2.out'});
        var o={v:0},u=+n.dataset.used,t=n.dataset.total;
        gsap.to(o,{v:u,duration:1.1,delay:.3+i*.1,ease:'power2.out',onUpdate:function(){n.textContent=Math.round(o.v)+' / '+t+' beds';}});
        gsap.from(c.querySelector('.badge'),{opacity:0,x:-20,duration:.4,delay:.8+i*.1});
      });
      gsap.from('#staff',{opacity:0,y:40,duration:.6,delay:.7});
      gsap.fromTo('#staff-bar',{width:0},{width:pct+'%',duration:1.3,delay:.9,ease:'power2.out'});
      var o2={v:0};
      gsap.to(o2,{v:present,duration:1.3,delay:.9,ease:'power2.out',onUpdate:function(){$('staff-n').textContent=Math.round(o2.v)+' / '+required+' nurses present';}});
    },
    kb:function(){
      gsap.from('#search',{opacity:0,y:-20,scaleX:.96,duration:.5,ease:'power3.out'});
      gsap.from('#kb .docs',{opacity:0,y:30,duration:.5,delay:.15});
      gsap.from('#list li',{opacity:0,x:-30,duration:.45,stagger:.06,delay:.3,ease:'power2.out'});
      gsap.from('#more',{opacity:0,duration:.4,delay:.9});
    }
  };

  /* ---------- NAV / VIEW SWITCHING ---------- */
  var active='home',busy=false;
  document.querySelectorAll('.nav .lk').forEach(function(b){
    b.onclick=function(){
      var v=b.dataset.v;if(v===active||busy)return;busy=true;
      document.querySelectorAll('.nav .lk').forEach(function(x){x.classList.toggle('on',x===b);x.removeAttribute('aria-current');});
      b.setAttribute('aria-current','page');
      var from=$(active),to=$(v);
      gsap.killTweensOf('#svg .an circle,#alist .mlb,#home .kpi .st i');
      gsap.to(from,{opacity:0,y:-16,duration:.25,ease:'power1.in',onComplete:function(){
        from.hidden=true;to.hidden=false;gsap.set([from,to],{opacity:1,y:0,clearProps:'transform'});
        active=v;busy=false;enter[v]();
      }});
    };
  });

  /* ---------- NAV INTRO + AMBIENT ---------- */
  gsap.from('#brand',{opacity:0,x:-30,duration:.7,ease:'power3.out'});
  gsap.from('.nav .lk',{opacity:0,y:-20,duration:.5,stagger:.08,delay:.2,ease:'power2.out'});
  gsap.from('#nav',{borderBottomColor:'rgba(126,240,198,0)',duration:1});
  gsap.to('body',{backgroundPosition:'28px 28px',duration:6,repeat:-1,ease:'none'});
  /* ---------- LOAD LIVE DATA, THEN START ---------- */
  Promise.all([get('/summary'),get('/alerts'),get('/departments'),get('/documents')]).then(function(r){
    loadHome(r[0]);loadAlerts(r[1]);loadDeps(r[2]);loadDocs(r[3]);enter.home();
  }).catch(function(){$('asof').textContent='Cannot reach the backend. Start the server and refresh the page.';enter.home();});

  /* ---------- CHAT ---------- */
  var chat=$('chat'),fab=$('fab'),log=$('log'),q=$('q');
  gsap.from(fab,{scale:0,rotate:-180,duration:.8,delay:.8,ease:'back.out(2)'});
  gsap.to(fab,{boxShadow:'4px 4px 0 #12262b, 0 0 0 8px rgba(126,240,198,.25)',duration:1.2,repeat:-1,yoyo:true,ease:'sine.inOut',delay:2});
  fab.onmouseenter=function(){gsap.to(fab,{scale:1.1,rotate:-6,duration:.25});};
  fab.onmouseleave=function(){gsap.to(fab,{scale:1,rotate:0,duration:.25});};
  function toggle(o){
    fab.setAttribute('aria-expanded',o);
    if(o){
      chat.classList.add('open');q.focus();
      gsap.fromTo(chat,{opacity:0,y:30,scale:.9,transformOrigin:'100% 100%'},{opacity:1,y:0,scale:1,duration:.4,ease:'back.out(1.8)'});
      gsap.from('#log .m',{opacity:0,y:12,duration:.35,stagger:.12,delay:.2});
    }else{
      gsap.to(chat,{opacity:0,y:20,scale:.92,duration:.25,ease:'power2.in',onComplete:function(){chat.classList.remove('open');}});
    }
  }
  fab.onclick=function(){toggle(!chat.classList.contains('open'));};
  $('close').onclick=function(){toggle(false);};
  var sid='s'+Math.random().toString(36).slice(2);
  // show **bold** as bold, drop single * marks (text only, safe)
  function fmt(el,t){
    el.textContent='';
    t.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*)/).forEach(function(p){
      if(!p)return;
      if(p.slice(0,2)==='**'&&p.slice(-2)==='**'){var b=document.createElement('strong');b.textContent=p.slice(2,-2);el.appendChild(b);}
      else if(p[0]==='*'&&p.slice(-1)==='*'&&p.length>2)el.appendChild(document.createTextNode(p.slice(1,-1)));
      else el.appendChild(document.createTextNode(p));
    });
  }
  function add(t,c){
    var m=document.createElement('div');m.className='m '+c;fmt(m,t);log.appendChild(m);log.scrollTop=log.scrollHeight;
    gsap.from(m,{opacity:0,y:14,x:c==='u'?20:-20,duration:.4,ease:'power2.out'});
    return m;
  }
  $('form').onsubmit=function(e){
    e.preventDefault();var t=q.value.trim();if(!t)return;add(t,'u');q.value='';
    var w=add('Thinking...','a');
    fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t,session_id:sid})})
      .then(function(r){return r.json();})
      .then(function(r){fmt(w,r.answer);log.scrollTop=log.scrollHeight;})
      .catch(function(){w.textContent='Cannot reach the server. Please try again.';});
  };

  /* ---------- HOVER ANIMATIONS (delegated, works on rebuilt elements too) ---------- */
  var glowOn={y:-8,boxShadow:'0 10px 0 rgba(126,240,198,.35)'},glowOff={y:0,boxShadow:'0 0 0 rgba(126,240,198,0)'};
  var rowOn={x:10,backgroundColor:'rgba(11,110,110,.10)'},rowOff={x:0,backgroundColor:'rgba(11,110,110,0)'};
  var H=[
    ['.nav .lk',{y:-4},{y:0}],
    ['#brand',{scale:1.06,transformOrigin:'0 50%'},{scale:1}],
    ['.btn',{scale:1.08,y:-2},{scale:1,y:0}],
    ['.hero-kpis .kpi, .deps .dep, #staff, .stat, .big',glowOn,glowOff],
    ['.pts li',{x:8},{x:0}],
    ['.pts svg',{rotate:-12,scale:1.15},{rotate:0,scale:1}],
    ['.tab',{y:-3,scale:1.06},{y:0,scale:1}],
    ['.range',{scale:1.05},{scale:1}],
    ['.chart',{y:-4,boxShadow:'0 8px 0 rgba(126,240,198,.3)'},{y:0,boxShadow:'0 0 0 rgba(126,240,198,0)'}],
    ['#svg .pl',{attr:{'stroke-width':9}},{attr:{'stroke-width':5}}],
    ['#svg .fl',{attr:{'stroke-width':9}},{attr:{'stroke-width':5}}],
    ['#alist li, #list li',rowOn,rowOff],
    ['#list li a',{x:5},{x:0}],
    ['.more',{x:5},{x:0}],
    ['.badge, .src',{scale:1.12},{scale:1}],
    ['.track',{scaleY:1.7},{scaleY:1}],
    ['.m',{scale:1.04},{scale:1}],
    ['.x',{rotate:90,scale:1.25},{rotate:0,scale:1}]
  ];
  function hov(e,out){
    if(!e.target.closest)return;
    H.forEach(function(h){
      var t=e.target.closest(h[0]);
      if(!t||(e.relatedTarget&&e.relatedTarget.nodeType===1&&t.contains(e.relatedTarget)))return;
      gsap.to(t,Object.assign({duration:.28,ease:out?'power2.out':'back.out(2)',overwrite:'auto'},out?h[2]:h[1]));
    });
  }
  document.addEventListener('mouseover',function(e){hov(e,false);});
  document.addEventListener('mouseout',function(e){hov(e,true);});
  // focus glow on inputs
  ['search','q'].forEach(function(id){
    var i=$(id);
    i.addEventListener('focus',function(){gsap.to(i,{boxShadow:'0 0 0 4px rgba(126,240,198,.6)',scale:1.01,duration:.25});});
    i.addEventListener('blur',function(){gsap.to(i,{boxShadow:'0 0 0 0 rgba(126,240,198,0)',scale:1,duration:.25});});
  });
})();
