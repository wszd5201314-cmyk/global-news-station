#!/usr/bin/env python3
import concurrent.futures, datetime, email.utils, hashlib, html, json, re, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).parent
FEEDS=[
("domestic","中国新闻网·滚动","https://www.chinanews.com.cn/rss/scroll-news.xml","综合"),
("domestic","中国新闻网·国内","https://www.chinanews.com.cn/rss/china.xml","时政"),
("domestic","中国新闻网·财经","https://www.chinanews.com.cn/rss/finance.xml","财经"),
("domestic","中国新闻网·科技","https://www.chinanews.com.cn/rss/it.xml","科技"),
("domestic","中国新闻网·社会","https://www.chinanews.com.cn/rss/society.xml","社会"),
("domestic","Google新闻·中国","https://news.google.com/rss/search?q=China+when%3A1d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans","综合"),
("international","BBC World","https://feeds.bbci.co.uk/news/world/rss.xml","国际"),
("international","The Guardian","https://www.theguardian.com/world/rss","国际"),
("international","Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml","国际"),
("international","Reuters·Google新闻","https://news.google.com/rss/search?q=site%3Areuters.com+when%3A1d&hl=en-US&gl=US&ceid=US:en","国际"),
("international","AP·Google新闻","https://news.google.com/rss/search?q=site%3Aapnews.com+when%3A1d&hl=en-US&gl=US&ceid=US:en","国际"),
("international","Google新闻·商业","https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en","财经"),
("international","Google新闻·科技","https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en","科技")
]
KEYS="国务院 央行 美联储 关税 降息 加息 战争 冲突 制裁 芯片 人工智能 特朗普 习近平 重大 突发 fed tariff inflation earthquake sanction war trump nvidia breaking".split()
def clean(s):
 return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",s or ""))).strip()
def sub(node,key):
 for x in node:
  if x.tag.rsplit("}",1)[-1].lower()==key.lower():
   return clean("".join(x.itertext()))
 return ""
def date(s):
 try:
  d=email.utils.parsedate_to_datetime(s)
  return d.astimezone(datetime.timezone.utc).isoformat()
 except Exception:
  try:return datetime.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(datetime.timezone.utc).isoformat()
  except Exception:return None
def collect(feed):
 section,source,url,category=feed
 request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; NewsRadar/1.0)","Accept":"application/rss+xml,application/xml,text/xml,*/*"})
 with urllib.request.urlopen(request,timeout=20) as r: xml=r.read(3000000)
 root=ET.fromstring(xml)
 items=[]
 for node in root.iter():
  if node.tag.rsplit("}",1)[-1].lower() not in ("item","entry"):continue
  title=sub(node,"title")
  link=sub(node,"link")
  if not link:
   for child in node:
    if child.tag.rsplit("}",1)[-1].lower()=="link" and child.attrib.get("href"):
     link=child.attrib["href"];break
  if not title or not link.startswith(("http://","https://")):continue
  summary=clean(sub(node,"description") or sub(node,"summary"))[:170]
  if summary.lower().startswith(title.lower()):summary=summary[len(title):].lstrip(" -:：")
  published=date(sub(node,"pubDate") or sub(node,"published") or sub(node,"updated") or sub(node,"date"))
  unique=hashlib.sha1((section+title.casefold()).encode()).hexdigest()[:16]
  important=any(w in (" "+title+" "+summary).lower() for w in KEYS)
  items.append(dict(id=unique,section=section,source=source,category=category,title=title[:240],url=link,published=published,summary=summary,important=important))
  if len(items)>=70:break
 return items
def main():
 now=datetime.datetime.now(datetime.timezone.utc)
 prev=BASE/"news.json";older=[]
 if prev.exists():
  try:older=json.loads(prev.read_text()).get("items",[])
  except Exception:pass
 news=[];sources=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  futures={pool.submit(collect,f):f for f in FEEDS}
  for future in concurrent.futures.as_completed(futures):
   name=futures[future][1]
   try:
    rows=future.result();news+=rows;sources.append(dict(source=name,ok=True,count=len(rows)))
   except Exception as exc:
    print("Failed:",name,str(exc)[:150]);sources.append(dict(source=name,ok=False,count=0))
 cutoff=now-datetime.timedelta(hours=72)
 uniq={}
 for x in news+older:
  try:
   if x.get("published") and datetime.datetime.fromisoformat(x["published"])<cutoff:continue
  except Exception:pass
  key=x["section"]+re.sub(r"\W+","",x["title"].casefold())[:100]
  if key not in uniq or (x.get("published") or "")>(uniq[key].get("published") or ""):uniq[key]=x
 records=sorted(uniq.values(),key=lambda x:x.get("published") or "",reverse=True)[:600]
 result=dict(updated_at=now.isoformat(),timezone="Asia/Shanghai",items=records,sources=sorted(sources,key=lambda s:s["source"]))
 if not news and not older:raise SystemExit("No feed could be fetched; retaining previous data")
 prev.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
 print("Total articles:",len(records),"Sources:",sum(x["ok"] for x in sources),"/",len(sources))
if __name__=="__main__":main()
