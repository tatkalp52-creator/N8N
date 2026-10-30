const fs=require('fs'), assert=require('assert');
const wf=JSON.parse(fs.readFileSync('/home/user/N8N/workflows/04_Video.json','utf8'));
const code=n=>wf.nodes.find(x=>x.name===n).parameters.jsCode;
async function run(name, nodes, input){
  const $=(n)=>{ if(!(n in nodes)) throw new Error('unexecuted '+n); return {first:()=>({json:nodes[n]})}; };
  const f=new Function('$','$json',`return (async()=>{${code(name)}})()`);
  return (await f($, input||{})).map(o=>o.json);
}
(async()=>{
  const tracks=[0,1,2].map(i=>({index:i,filename:'Track '+i,startSeconds:i*200}));
  const info={tracks,totalDurationSeconds:600};
  const tmpl={'🖋_tmpl_PackagingRules':'[TIMECODES] rules here','🖋🎨_tmpl_CharacterPassport':'Pengui','tmpl_LightModel':'gpt-5-mini'};
  const N='Названия треков из таблицы';
  // 1) названий больше, чем треков
  let proj={ai_TimecodeNames:'A One\nB Two\nC Three\nD Four',sys_LoopCount:''};
  let b=(await run(N,{'Читаем проект':proj,'Считаем длительности треков':info}))[0];
  let t=(await run('Собираем текст таймкодов',{[N]:b,'Читаем проект':proj,'Читаем стиль оверлея':{'🎬tmpl_GapSeconds':'1.4'}}))[0].timecodesText;
  assert.equal(t,'0:00 A One\n3:20 B Two\n6:40 C Three\n10:01 Repeat', 'Repeat = конец + пауза, вниз — в паузу'); console.log('1 OK\n'+t);
  // 2) (28.10) названий меньше, чем треков — своего «придумщика» нет: сообщение автору, сборка не идёт
  for (const names of ['A One', undefined]) {
    proj={ai_TimecodeNames:names,sys_LoopCount:''};
    await assert.rejects(run(N,{'Читаем проект':proj,'Считаем длительности треков':info}), /Таблица: названий тайм-кодов \(ai_TimecodeNames\) [01], а треков 3/);
  }
  assert.ok(!wf.nodes.some(n=>n.name==='OpenAI: названия треков'), 'узла-придумщика больше нет');
  console.log('2-3 OK (названия — только из таблицы)');
  // 4) после часа — «1:00:22», не «60:22»
  const longInfo={tracks:[0,1,2].map(i=>({index:i,filename:'T'+i,startSeconds:[0,3622,7385][i]})),totalDurationSeconds:7400};
  proj={ai_TimecodeNames:'A\nB\nC',sys_LoopCount:''};
  b=(await run(N,{'Читаем проект':proj,'Считаем длительности треков':longInfo}))[0];
  t=(await run('Собираем текст таймкодов',{[N]:b,'Читаем проект':proj,'Читаем стиль оверлея':{}}))[0].timecodesText;
  assert.equal(t,'0:00 A\n1:00:22 B\n2:03:05 C'); console.log('4 OK (часы)');

  // 5) переводы: языки из tmpl_Languages, правила из 🌐, тело videos.update
  const data={title:"Pengui's Jazz · Park | Quiet Bench",description:'Story\n\n0:00 A\n\n#pengui',tags:'jazz, cozy, jazz',chatId:7};
  let pr=await run('Готовим переводы',{'Читаем стиль оверлея':{'tmpl_Languages':''},'Готовим данные для сборки':data});
  assert.equal(pr.length,0,'нет языков — ветка молчит');
  pr=(await run('Готовим переводы',{'Читаем стиль оверлея':{'tmpl_Languages':'es, DE; fr en','tmpl_LightModel':'gpt-5-mini','tmpl_LightEffort':'minimal','🌐_tmpl_TranslationRules':"Keep Pengui's Jazz",'🎬tmpl_X':'no'},'Готовим данные для сборки':data}))[0];
  assert.deepEqual(pr.langs,['es','de','fr']); assert.equal(pr.effort,'minimal','усилие — из tmpl_LightEffort'); assert.ok(pr.systemPrompt.includes("Keep Pengui's Jazz")); assert.ok(!pr.systemPrompt.includes('no\n'));
  const ans={choices:[{message:{content:JSON.stringify({es:{title:'T es <x>',description:'D es'},de:{title:'T de',description:'D de'},fr:{title:''}})}}]};
  const bl=(await run('Собираем локализации',{'Готовим данные для сборки':data,'Загружаем на YouTube':{uploadId:'vid1'},'Готовим переводы':pr},ans))[0];
  assert.equal(bl.error,''); assert.deepEqual(bl.langs,['es','de']); assert.equal(bl.body.id,'vid1');
  assert.equal(bl.body.snippet.description,data.description); assert.deepEqual(bl.body.snippet.tags,['jazz','cozy']); assert.equal(bl.body.snippet.defaultLanguage,'en');
  assert.equal(bl.body.localizations.es.title,'T es x');
  const bad=(await run('Собираем локализации',{'Готовим данные для сборки':data,'Загружаем на YouTube':{uploadId:'v'},'Готовим переводы':pr},{error:{message:'timeout'}}))[0];
  assert.ok(bad.error.includes('не ответил'));
  let it=(await run('Итог переводов',{'Собираем локализации':bl,'Готовим данные для сборки':data},{kind:'youtube#video'}))[0];
  assert.ok(it.text.includes('es, de')); assert.equal(it.chatId,7);
  it=(await run('Итог переводов',{'Собираем локализации':bl,'Готовим данные для сборки':data},{error:{message:'403'}}))[0];
  assert.ok(it.text.includes('не встали'));
  console.log('5 OK (переводы)');
  // 5b) (22.10) пересборка: тот же текст — переводы из строки выпуска, OpenAI не зовём; новые тайм-коды подставляются
  {
    assert.equal(pr.cached,false); assert.equal(pr.model,'gpt-5-mini');
    const T={'tmpl_Languages':'es, DE; fr en','tmpl_LightModel':'gpt-5-mini','🌐_tmpl_TranslationRules':"Keep Pengui's Jazz"};
    const cacheRow={sys_Translations: bl.cacheJson.replace('D es','D es 0:00 A').replace('D de','D de 0:00 A')};
    const data2={...data,description:'Story\n\n0:05 A\n\n#pengui'};
    const p2=(await run('Готовим переводы',{'Читаем стиль оверлея':T,'Готовим данные для сборки':data2,'Читаем проект':cacheRow}))[0];
    assert.equal(p2.cached,true,'текст тот же — берём готовое');
    assert.equal(p2.cachedLoc.es.description,'D es 0:05 A','тайм-код новый');
    const b2=(await run('Собираем локализации',{'Готовим данные для сборки':data2,'Загружаем на YouTube':{uploadId:'vid2'},'Готовим переводы':p2},p2))[0];
    assert.equal(b2.error,''); assert.equal(b2.body.id,'vid2'); assert.equal(b2.body.localizations.es.description,'D es 0:05 A');
    const p3=(await run('Готовим переводы',{'Читаем стиль оверлея':{...T,'tmpl_LightModel':'gpt-5-nano'},'Готовим данные для сборки':{...data,title:'New title'},'Читаем проект':cacheRow}))[0];
    assert.equal(p3.cached,false,'текст другой — переводим'); assert.equal(p3.model,'gpt-5-nano','модель из таблицы');
  }
  console.log('5b OK (пересборка без перевода)');
})().catch(e=>{console.error('FAIL',e);process.exit(1)});
