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
  const tmpl={'🖋_tmpl_PackagingRules':'[TIMECODES] rules here','🖋🎨_tmpl_CharacterPassport':'Pengui'};
  // 1) названий больше, чем треков
  let proj={ai_TimecodeNames:'A One\nB Two\nC Three\nD Four',sys_LoopCount:''};
  let b=(await run('Готовим запрос на названия треков',{'Читаем проект':proj,'Считаем длительности треков':info},tmpl))[0];
  assert.equal(b.skipGpt,true);
  let t=(await run('Собираем текст таймкодов',{'Готовим запрос на названия треков':b,'Читаем проект':proj,'Читаем стиль оверлея':{'🎬tmpl_GapSeconds':'1.4'}}))[0].timecodesText;
  assert.equal(t,'0:00 A One\n3:20 B Two\n6:40 C Three\n10:01 Repeat', 'Repeat = конец + пауза, вниз — в паузу'); console.log('1 OK\n'+t);
  // 2) названий меньше
  proj={ai_TimecodeNames:'A One',sys_LoopCount:''};
  b=(await run('Готовим запрос на названия треков',{'Читаем проект':proj,'Считаем длительности треков':info},tmpl))[0];
  assert.equal(b.skipGpt,false); assert.ok(b.userPrompt.includes('индексами: 1, 2')); assert.ok(b.systemPrompt.includes('[TIMECODES] rules here')); assert.ok(!b.systemPrompt.includes('Nap Attack'));
  t=(await run('Собираем текст таймкодов',{'Готовим запрос на названия треков':b,'Читаем проект':proj,'OpenAI: названия треков':{choices:[{message:{content:JSON.stringify({names:{'1':'G One','2':'G Two'}})}}]},'Читаем стиль оверлея':{}}))[0].timecodesText;
  assert.equal(t,'0:00 A One\n3:20 G One\n6:40 G Two\n10:00 Repeat'); console.log('2 OK');
  // 3) старый проект без колонки — все треки называет GPT, имена файлов не используются
  proj={sys_LoopCount:'1'};
  b=(await run('Готовим запрос на названия треков',{'Читаем проект':proj,'Считаем длительности треков':info},tmpl))[0];
  assert.ok(b.userPrompt.includes('индексами: 0, 1, 2'));
  t=(await run('Собираем текст таймкодов',{'Готовим запрос на названия треков':b,'Читаем проект':proj,'OpenAI: названия треков':{choices:[{message:{content:JSON.stringify({names:{'0':'X','1':'Y','2':'Z'}})}}]}}))[0].timecodesText;
  assert.equal(t,'0:00 X\n3:20 Y\n6:40 Z'); console.log('3 OK');
  // 4) после часа — «1:00:22», не «60:22»
  const longInfo={tracks:[0,1,2].map(i=>({index:i,filename:'T'+i,startSeconds:[0,3622,7385][i]})),totalDurationSeconds:7400};
  proj={ai_TimecodeNames:'A\nB\nC',sys_LoopCount:''};
  b=(await run('Готовим запрос на названия треков',{'Читаем проект':proj,'Считаем длительности треков':longInfo},tmpl))[0];
  t=(await run('Собираем текст таймкодов',{'Готовим запрос на названия треков':b,'Читаем проект':proj,'Читаем стиль оверлея':{}}))[0].timecodesText;
  assert.equal(t,'0:00 A\n1:00:22 B\n2:03:05 C'); console.log('4 OK (часы)');

  // 5) переводы: языки из tmpl_Languages, правила из 🌐, тело videos.update
  const data={title:"Pengui's Jazz · Park | Quiet Bench",description:'Story\n\n0:00 A\n\n#pengui',tags:'jazz, cozy, jazz',chatId:7};
  let pr=await run('Готовим переводы',{'Читаем стиль оверлея':{'tmpl_Languages':''},'Готовим данные для сборки':data});
  assert.equal(pr.length,0,'нет языков — ветка молчит');
  pr=(await run('Готовим переводы',{'Читаем стиль оверлея':{'tmpl_Languages':'es, DE; fr en','🌐_tmpl_TranslationRules':"Keep Pengui's Jazz",'🎬tmpl_X':'no'},'Готовим данные для сборки':data}))[0];
  assert.deepEqual(pr.langs,['es','de','fr']); assert.ok(pr.systemPrompt.includes("Keep Pengui's Jazz")); assert.ok(!pr.systemPrompt.includes('no\n'));
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
})().catch(e=>{console.error('FAIL',e);process.exit(1)});
