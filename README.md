# ReadExpress-CoT 閱讀快線（國小素養版）

專為臺灣國小六年級學生設計的閱讀理解練習系統：文章 × 10 階漸進提問 × 雙輸入（語音／打字）容錯解析 × 逐題解析 × 後設認知 CoT 思維鏈反思。

文章依 108 課綱閱讀領域分成 8 類，目標規模 200 篇，目前 5 篇（陸續補上）。

規格來源：[`ReadExpress-CoT-Elementary.md`](ReadExpress-CoT-Elementary.md)

---

## 兩種執行方式

| | 網址 | 適合 |
|:---|:---|:---|
| **靜態網頁版** | <https://joshua19683721.github.io/c1> | 開瀏覽器就能用，不裝任何東西。可設成平板或電腦的捷徑給學生用。 |
| **Streamlit 版** | `streamlit run app.py` | 老師在課堂上投放，並可接上 LLM 做更自然的回饋。 |

兩版共用**同一份文章與題目**（`src/content.py`），不會各自漂移。

> 靜態網頁版**不使用任何 API**。瀏覽器頁面無法安全保存金鑰，把金鑰放進公開網址等於公開給所有人，所以網頁版全部在本機運算。

---

## 快速開始（Streamlit 版）

```bash
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器會開在 <http://localhost:8501>。**不需要任何 API 金鑰就能完整使用**——系統會自動切換到離線模式。

要讓 AI 用更自然的語氣回饋與生成反思（可選）：

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-..."
streamlit run app.py
```

```bash
# macOS / Linux
export DEEPSEEK_API_KEY="sk-..."
streamlit run app.py
```

---

## 文章分類與 200 篇計畫

8 個類別對應 108 課綱的閱讀領域：

| 分類 | 訓練重點 |
|:---|:---|
| 📜 記敘與抒情 | 跟著敘事線索還原畫面與情感 |
| 🔬 說明與科普 | 分辨資訊之間的因果關係 |
| 🏮 古典與成語 | 字詞理解與古今語意對照 |
| 🌻 現代詩 | 辨識分行、意象、比喻與通感 |
| 🎭 小說與戲劇 | 人物、情節、轉折的預測與推論 |
| 🗺️ 臺灣文化與鄉土 | 地方文化如何形成 |
| 🌍 人物、社會與環境 | 分辨論點與價值立場 |
| 🧙 寓言與童話 | 推論寓意與生活應用 |

文章寫在 `src/categories/<slug>.py`，每類一個模組。
**不是**全部塞在 `src/content.py` —— 200 篇集中在一個檔案會變成沒有人敢動的 1.4 MB，
而且每次新增都可能撞到不相干的修改。新增一篇文章 = 新增一個小檔案。

`src/content.py` 在 import 時會驗證每一篇：題數、選項數、選項是否重複、
是否有提示、**是否有解析**、gist 長度。有缺漏會立刻報錯並一次列出所有問題，
所以補文章時漏填欄位不可能悄悄通過測試。

```bash
python tools/export_site_data.py          # 同步到網頁版
python tools/export_site_data.py --check  # CI 檢查是否過期
```

---

## 答錯時的逐題解析

答錯不會直接跳下一題。畫面會停下來給一張**解析卡**：

- **答對** → 顯示「📖 為什麼是這個答案？」，說明這個選項為何成立，再由學生按 `➡️ 下一題`
- **答錯** → 顯示「📖 正確答案與解析」＋正確選項 ＋ 為什麼，並提供 `🔄 再試一次` 與 `➡️ 懂了，看下一題`

兩種情況都不會自動前進，因為**解析屬於剛才那一題**；一旦自動跳題，
解析就會被錯誤地對到下一題上。

這是刻意的設計轉折。早期版本答錯時只給提示、不給正解，理由是讓學生再試一次；
但使用者明確要求「答錯也要能提供正確的解釋」，所以改成：先讓學生選擇要不要再試，
而不是硬性藏住答案。

每一題的解析都是逐題手寫的，不是模板填出來的。

## 靜態網頁版（GitHub Pages）

```
site/
  index.html          介面骨架
  styles.css          莫蘭迪藍／暖色調（與 src/ui.py 同一套色票）
  app.js              流程：答題、立即回饋、拼圖、CoT
  lib/parser.js       src/parser.py 的 JavaScript 版本
  lib/reflection.js   src/cot.py 本地反思的 JavaScript 版本
  data/articles.json  由 tools/export_site_data.py 從 src/content.py 產生
```

**單一資料來源。** `site/data/articles.json` 不是手抄的，而是從 `src/content.py` 產生；
每題還一併輸出 `shuffleOrder`，讓瀏覽器重現 `build_lesson()` 完全相同的選項順序，
不必在 JavaScript 裡重新實作 Mersenne Twister。

```bash
python tools/export_site_data.py            # 重新產生
python tools/export_site_data.py --check    # CI 檢查是否過期
```

部署由 `.github/workflows/pages.yml` 自動完成，使用 GitHub 內建的 GITHUB_TOKEN，
不需要 Personal Access Token，也不用在 repository 設定裡手動指定來源。
每次部署前會先重新產生資料並跑 `tests/test_site.py`，資料過期或網頁測試失敗就不會上線。

**語音在網頁版反而更好用。** 靜態版改用瀏覽器的 Web Speech API（`SpeechSynthesis` 朗讀、
`SpeechRecognition` 辨識），不需要 Whisper，也不需要 sounddevice，語音完全在本機完成。
語音辨識在 Chrome、Edge、Safari 可用；Firefox 沒有這個 API，介面會自動停用按鈕並提示改用打字。

**為什麼兩份解析實作不共用同一份程式碼？** `difflib.SequenceMatcher` 在 JavaScript 沒有對應實作，
硬要逐一對齊數值只會得到脆弱的等價。真正該保證的是**行為**，所以 `tests/site/run_contract.mjs`
對 JavaScript 版斷言與 Python 版相同的契約：

- 200 個選項逐字唸出 → 200/200 回到原選項
- **主動接受錯誤答案：0 次**
- 無關的回答一律拒絕

`tests/site/run_app.mjs` 再用最小 DOM 樁把真正的 `site/app.js` 跑完 5 篇 × 10 題，
確保按鈕有接線、元素 id 沒打錯。

---

## 系統分層

由外而內，每一層只依賴它下面的層：

```
app.py                 Streamlit 介面、session state、流程控制
src/cot.py             Pipeline 2 — 反思拼圖 + 3 步驟 CoT
src/evaluator.py       Pipeline 1 — 回答判定 + 即時回饋
src/llm.py             OpenAI 相容後端（選用，可完全缺席）
src/prompts.py         YAML pipeline 載入與變數渲染
src/speech.py          瀏覽器 TTS 朗讀 + 本機 Whisper 語音輸入
src/parser.py          寬容數字解析 + 語意模糊比對
src/content.py         5 篇文章與 50 題的階梯題庫
dsh_config/            兩條 pipeline 的提示詞定義（唯一真實來源）
```

提示詞永遠不在 Python 裡寫死，改 `dsh_config/read_express_cot_pipelines_elem.yaml` 就能調整助教的語氣。

---

## 兩條 Pipeline

### Pipeline 1 — `option_evaluator`

判斷學生選了哪一項，並給出適合小六生的回饋。採用**逐級落**（前一級不敢下定論才往下走）：

| 順序 | 方式 | 說明 |
|:---|:---|:---|
| 1 | **寬容數字解析** | `3`、`第三個`、`我選二`、`答案是4`。確定性、零延遲，完全不呼叫模型。 |
| 2 | **AI 判讀** | 呼叫 `option_evaluator` pipeline；回傳的 JSON 會先對照真實選項驗證才採用。 |
| 3 | **本地模糊比對** | 離線備援，處理改寫與語音辨識錯字。 |
| 4 | **不判定** | 交出最佳候選讓學生確認，**不會**擅自記成錯。 |

數字優先是規格明訂的設計（「優先擷取選項數字」），也讓最常用的路徑完全不依賴網路。

### Pipeline 2 — `cot_reflection_generator`

把十題的答案組裝成 **閱讀思考拼圖**，並生成 **3 步驟 CoT 解析**：

1. **尋找線索（細節理解）** — 第 1～3 題，找出文章的基本事實與背景
2. **串聯情意（推論分析）** — 第 4～7 題，抓出因果關係、寫作方法與深層情感
3. **大腦昇華（省思評鑑）** — 第 8～10 題，理解主旨並連結生活道理

---

## 答題解析的兩個關鍵設計

### 1. 數字不能被「答案內容」誤傷

〈空城計〉的正確答案是「司馬懿有十五萬大軍，諸葛亮只有二千五百名士兵」。
若學生整句唸出來，語音辨識可能產生 `15萬` 或 `二千五百`。

因此：

- 阿拉伯數字必須是**獨立**的（前後不能接其他數字），`15萬` 不會被讀成「選項 1」
- 中文數字只在「單獨成詞」（`二`）或「有提示詞」（`第二個`）時才認，絕不整句掃描——`二千五百名士兵` 是**引用答案**，不是「選 2」

這是實際會害到學生的 bug，`tests/test_parser.py` 裡有專門的迴歸測試守著。

### 2. 寧可重新問，也不要猜錯

模糊比對有明確的**信賴門檻**與**歧義緩衝**。當最佳候選與第二名差距太小、或分數不夠時，系統不會自動選，而是：

- 保留最佳候選當作 `suggestion`
- 在介面上問「你是不是想選這個？」
- 由學生按下去確認

早期版本曾設過「領先很多就自動接受」的弱門檻。實測後發現在〈背影〉第 6 題會把**錯誤選項**高信心地收下——對學生來說，靜默地判錯比多問一次傷害大得多，所以拿掉了。

現在的實測結果（全 200 個選項）：

- 逐字唸出選項 → **200/200** 正確回到原選項
- 手寫改寫句 → 最高排序正確率 **19/24**
- **主動接受錯誤答案：0 次**

---

## 選項順序洗牌（重要修正）

原始規格裡，**50 題的正確答案全部都是選項 1**。
照單全收等於在教學生「答案永遠是 A」，測到的不是閱讀能力。

`src/content.py` 因此在載入時用**固定種子**（由文章 id + 題號雜湊而來）洗牌，
讓正確答案平均落在四個位置。種子是確定性的，所以重整頁面或換台電腦，答案位置都不會跳動。

- 預設：**開啟洗牌**
- 側邊欄可關閉，還原成規格檔的原樣順序
- 每題另存 `source_correct_index`，保留洗牌前的出處

---

## 語音功能與降級策略

| 功能 | 做法 | 缺少時 |
|:---|:---|:---|
| **朗讀** | 瀏覽器 Web Speech API（iframe 元件） | 永遠可用，不需伺服器套件、不需網路 |
| **文章音檔** | gTTS（選用，需網路） | 按鈕顯示失敗原因，不影響其他功能 |
| **語音輸入** | sounddevice 錄音 + **本機** openai-whisper | 按鈕自動停用並說明原因，改用打字 |

語音辨識完全在本機進行，學生的聲音不會上傳到任何伺服器。

---

## 環境變數

| 變數 | 預設 | 用途 |
|:---|:---|:---|
| `DEEPSEEK_API_KEY` | — | LLM 金鑰。也接受 `OPENAI_API_KEY`、`READEXPRESS_LLM_API_KEY` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 相容端點 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名稱 |
| `READEXPRESS_LLM_TEMPERATURE` | `0.3` | creativity 愈低愈穩定 |
| `READEXPRESS_LLM_TIMEOUT` | `30` | 呼叫逾時秒數 |

**沒有金鑰時**：Pipeline 1 走本地解析，Pipeline 2 走離線生成，全部功能照常，只是回饋語氣較固定。

---

## 測試

```bash
python -m pytest tests -q
```

```
149 passed
```

> 註：`requirements-ci.txt` 是精簡版（不含 whisper / sounddevice / openai），
> 因為語音相關套件約 2 GB，而測試從不觸碰它們（`src/speech.py` 為延遲載入並優雅降級）。
> CI 會在 Ubuntu 與 Windows 兩個平台各跑一次完整測試套件。

涵蓋範圍：

- `test_content.py` — 5 篇 / 50 題結構、洗牌不改變正解、洗牌確實打散位置
- `test_parser.py` — 數字解析、逐字回歸（200 題）、**零錯誤接受**保證、變體折疊
- `test_prompts.py` — YAML 契約、佔位符全數填入、缺值會顯眼
- `test_evaluator.py` — 級聯順序、答錯給提示不給答案、空輸入不猜
- `test_cot.py` — 三步驟、十題意涵都在、gist 長度
- `test_app_ui.py` — **真的把 Streamlit App 跑起來**點完 10 題，驗證拼圖區與重置流程

---

## 已知落差

規格要求反思拼圖約 **100–150 字**。

- **LLM 路線**：會寫成通順的 100–150 字散文，符合規格。
- **離線路線**：逐字引用學生的十個答案，實測約 **175 字**。

這是刻意的取捨：離線時沒有模型可用，能做的只有引用。
為此每題另存了一個 `gist`（濃縮意涵），把離線拼圖從原本的 **290 字**降到 **175 字**。
再往下壓需要把 gist 砍到 12 字以下，試過，中文會明顯變得彆扭——為了 20 字不值得。

另外三處刻意的偏離，都記在程式碼註解裡：

1. 答錯時**不洩漏正解**，改給該題專屬提示（允許學生再試一次）
2. 選項順序洗牌（見上）
3. 判定不出來時交出候選確認，而非猜一個（見上）

---

## 授權與出處

文章與題目取自規格檔 `ReadExpress-CoT-Elementary.md`；〈背影〉改寫自朱自清，
《吃冰的滋味》改寫自古蒙仁，《空城計》改寫自羅貫中〈空城計〉。
