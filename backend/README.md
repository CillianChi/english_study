# Backend（FastAPI + Postgres + FSRS）

## 啟動步驟

```bash
# 1. 啟動本機 Postgres（會自動用 schema.sql 建表）
docker compose up -d

# 2. 設定環境變數
cp .env.example .env
# 把 JWT_SECRET 換成隨機字串

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 匯入 TOEIC 3000 詞庫（含中文釋義 + KK 音標，來源：../toeic3000_meanings.json、../toeic3000_phonetics.json）
python import_words.py

# 5. 啟動 API
uvicorn app.main:app --reload
```

API 文件：http://localhost:8000/docs

## API 一覽

| Method | Path            | 說明 |
|---|---|---|
| POST | `/auth/register` | 註冊，回傳 JWT |
| POST | `/auth/login`    | 登入，回傳 JWT |
| GET  | `/due`           | 取得今日待複習清單（含 due_count / overdue_count），Bearer token |
| POST | `/review`        | 提交一次複習結果，觸發 FSRS 更新，Bearer token |
| GET  | `/game/mc/questions` | 四選一小遊戲題目（中文選英文，誘答為拼字最相似的字），Bearer token |
| POST | `/game/mc/answer`    | 提交作答，答對/答錯轉成 FSRS rating 寫回，Bearer token |
| GET  | `/tts/{word}`    | 回傳該字的發音 mp3（edge-tts 神經網路語音），不需要 token |

## 發音（/tts）

用 [edge-tts](https://github.com/rany2/edge-tts) 接 Microsoft Edge 的線上神經網路語音——非官方
API、不用申請 key，音質是免費方案裡數一數二自然的。第一次請求某個字會即時向 Microsoft 要音檔
（約 1-2 秒），之後就從 `audio_cache/`（已加進 .gitignore，不會進版控）直接讀快取，不會重複呼叫。

沒有掛驗證：任何人拿到網址都能打，但已經限制只接受 `words` 表裡存在的字，不然會變成一個開放的
免費文字轉語音代理，被濫用會把你的 IP 用量算在 Microsoft 那邊。要用固定其他聲音就改
`app/tts_service.py` 的 `VOICE`（跑 `edge-tts --list-voices` 可以列出全部可選聲音）。

前端（[index.html](../index.html)）的喇叭按鈕預設打 `http://localhost:8000`，寫在檔案裡的
`TTS_API_BASE` 常數，backend 沒啟動時按鈕會靜默失敗（主控台印警告），不影響其他功能。

## 四選一遊戲怎麼挑誘答選項

用 Postgres `pg_trgm` 擴充套件算拼字的 trigram 相似度（`word <-> :target`），直接在資料庫端抓
「跟正確答案長得最像的 3 個字」當干擾選項——例如 affect 的誘答會抓到 affection / effect / infect，
adapt 會抓到 adapter / adopt / adept，這正是多益考生真正會混淆的組合，比隨機挑三個字有效得多。
細節見 [app/game_service.py](app/game_service.py)。作答結果（答對/答錯 + 反應時間）一樣會轉成
FSRS rating 寫回 `learning_state`（`app/review_service.py`），所以這個遊戲不是外掛小工具，
玩的同時也在推進正常的間隔複習進度。

## KK 音標怎麼生成的

`generate_phonetics.py` 用 `eng_to_ipa`（底層是 CMU Pronouncing Dictionary）產生美式 IPA，
再做 KK（Kenyon & Knott）慣用的兩個記法轉換：`eɪ`→`e`、`oʊ`→`o`。這是自動化近似，不是人工校對過
的發音辭典——CMUdict 整體很準，但仍可能有極少數錯誤，遇到明顯有誤的字歡迎回報。複合字（如
above-average）用連字號拆開分別轉換再組回去。2931 字中 2900 字成功產生音標，其餘 31 字（多半是
`toeic3000_categorized.csv` 裡本來就殘缺的字，例如 "cabine"、"kidna"、"retai"）沒有音標。
重跑：`python generate_phonetics.py`，會寫回 `../toeic3000_phonetics.json`。

## 目前的簡化/待辦

- `cloze_items` 目前沒有生成腳本——填空題內容需要另外寫一個批次工具（挑選 `learning_state.stability` 剛跨過門檻的字，呼叫 AI 生成例句+提示，寫入這張表）。在此之前，`/due` 對「成熟字」會自動退回 `recall` 題型。
- CORS 目前開放所有來源（`allow_origins=["*"]`），部署前記得改成前端實際網域。
- 本機沒有 Docker 可用時，改用 Neon/Supabase 建一個 Postgres 執行個體，把連線字串填進 `.env` 的 `DATABASE_URL`，`schema.sql` 手動用 `psql` 跑一次即可，其餘步驟不變。
