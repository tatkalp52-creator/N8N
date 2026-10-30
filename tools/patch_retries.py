"""Правило повторов (24.10) для workflows/14_Разбор_каналов.json: повторяется только безопасное. 04 не трогаем — автор оставила в 04 повторы везде (24.10).

Без повторов: загрузка на YouTube (повтор = второй ролик), публикация комментария (второй комментарий),
отправки в Телеграм (дубли сообщений). Чтение (GET), замена (PUT), удаление, OpenAI без памяти,
запись в таблицу по ключу — повторы остаются. Повторный запуск ничего не меняет.

    python3 tools/patch_retries.py
"""
import json, os

PATHS = [os.path.join(os.path.dirname(__file__), "..", "workflows", f) for f in ("14_Разбор_каналов.json",)]


def unsafe(n):
    t, p = n["type"], n["parameters"]
    url = str(p.get("url", ""))
    if t == "n8n-nodes-base.youTube":
        return True
    if t == "n8n-nodes-base.telegram":
        return True
    if t == "n8n-nodes-base.httpRequest" and p.get("method") == "POST":
        return "api.telegram.org" in url or "/bot" in url or "commentThreads" in url
    if t == "n8n-nodes-base.googleSheets" and p.get("operation") in ("append", "appendOrUpdate"):
        return True
    return False


def main():
  for PATH in PATHS:
    w = json.load(open(PATH))
    changed = []
    for n in w["nodes"]:
        if unsafe(n) and n.get("retryOnFail"):
            for k in ("retryOnFail", "maxTries", "waitBetweenTries"):
                n.pop(k, None)
            changed.append(n["name"])
    json.dump(w, open(PATH, "w"), ensure_ascii=False, indent=2)
    print(os.path.basename(PATH), "— без повторов:", len(changed), changed)


if __name__ == "__main__":
    main()
