# Interview Prep: AI Property Video Generator

Read this once tonight, once in the morning. Sections 1-3 are what you say; sections 4-5 are what you get asked.

---

## 0. Tonight's checklist (15 minutes)
1. Run `run.bat` once on your laptop and generate the sample video (this has **not** been tested on Windows).
2. Open `src/script_generator.py`, `src/validators.py`, `src/video_generator.py` and read the function names and comments. You do not need every line, but you must be able to say what each function does.
3. Push the updated project to GitHub (see the end of this file).
4. Keep `outputs/sample_property_video.mp4` on your desktop as a backup. If the live demo is slow, play it.

## 1. Your 60-second pitch
"Real-estate sales teams make a promotional video by hand for every property. I built a tool that does it automatically.
The agent enters the property facts, uploads 4 to 8 photos, and optionally labels each photo, for example *Kitchen*.
The app writes a script and captions using **template logic**, because an advert must never invent a feature. Every
sentence is built only from the user's facts, and a **grounding check** verifies that no unknown number or word got in.
Then it turns each photo into a scene with a text panel and a slow zoom, cross-fades the scenes, and exports an H.264
MP4 that plays in any browser. The user can preview and download it. Bad input, such as a corrupted image or a missing
price, gives a clear message instead of a crash. There are 102 automated tests, including real video renders."

## 2. Architecture in one minute
```
Form + photos (+ optional photo labels)
   -> validators.py        clean + check everything (blocking errors vs. warnings)
   -> script_generator.py  templates + user's facts -> scenes; match_score() pairs features with labelled photos;
                           check_grounding() rejects unknown numbers/words
   -> video_generator.py   crop -> zoom -> Pillow text panel -> cross-fade -> FFmpeg (libx264, yuv420p) -> MP4
   -> app.py (Streamlit)   progress bar, preview, download, scene table
```
Why this stack: Streamlit gives form + preview + download with no frontend code; Pillow draws text without
ImageMagick (the usual Windows problem); MoviePy 2 + the FFmpeg that comes with it export the MP4.

## 3. How to talk about "AI" honestly (20% of the marks)
The assignment says a rule-based approach is fine *if it is justified and works well*. So say this:

* **What it is:** rule-based natural-language generation (templates) plus a rule-based matcher that links features to
  photos, plus a grounding verifier.
* **Why not an LLM:** in real estate a wrong claim (a pool that does not exist, a wrong distance) is a legal and trust
  problem. Templates make hallucination impossible by construction, run offline, are free and are deterministic, so
  they are testable.
* **How I check the output:** `check_grounding()` re-reads every caption and voice-over line. Any number or word that
  is not in the user's facts, the photo labels or the template vocabulary is rejected. Tests prove it catches an
  injected "Swimming pool" and "5 km from the airport".
* **Be upfront about the limit:** for pure templates the checker mostly confirms consistency, because the vocabulary is
  built from the templates. Its real value is as the safety net for a future LLM rewrite: the LLM's output would go
  through the same check.
* **Where real ML would go next:** a zero-shot image classifier (for example CLIP) to label the photos automatically
  (*kitchen*, *bedroom*...), which then feeds the same `match_score()`. Also an LLM for more varied wording, guarded by
  `check_grounding()`.

---

## 4. Questions you may get (with answers in simple Hinglish)

### Problem and business
**Q1. Yeh kis problem ko solve karta hai? Kaun use karega?**
Sales team ko har property ke liye alag video manually banana padta hai (editor, time). Ye tool facts + photos se 1 minute mein 30 second ka ready video bana deta hai. Use karne wale: agents, listing teams. Fayda: time bachta hai, har listing ka same quality aur same format.

**Q2. Success kaise measure karoge?**
Time per video (manual 1-2 ghante vs 1 minute), kitne listings ke video bane, aur agent ko manual edit kitni baar karna padta hai. Quality ke liye: koi galat claim nahi (grounding check pass rate).

**Q3. Real photos pe kaisa chalega?**
Photos center-crop hoti hain (stretch nahi), phone ki sideways photos EXIF se seedhi hoti hain, kam resolution par warning aati hai. Maine demo ke liye synthetic illustrations use kiye kyunki real photos mein copyright/privacy ka risk hota.

### AI approach
**Q4. Isme AI kahan hai?**
Rule-based NLG (templates) + feature-to-photo matching + grounding verifier. Maine jaan-bujhkar LLM nahi liya, kyunki wo amenities invent kar sakta hai. Assignment bhi rule-based allow karti hai agar justify ho.

**Q5. `check_grounding()` kya pakadta hai aur kya nahi?**
Pakadta hai: koi bhi number ya word jo user ke facts, photo labels ya template vocabulary mein nahi hai. Nahi pakadta: agar template hi galat ho (isliye tests mein templates mein "luxury", "stunning" jaise words ban hain), aur ye meaning check nahi karta, sirf words/numbers.

**Q6. Photo ko feature se match kaise karte ho?**
User photo ke neeche label likhta hai (jaise "Kitchen"). `match_score()` dono texts ko lowercase karke, plural hata ke ("bedrooms" -> "bedroom") common words gina hai. "Modular kitchen" aur "Kitchen" mein "kitchen" common hai, toh wo feature kitchen photo par jaata hai. Jis feature ka match nahi, wo sirf bina-label wali photos par jaata hai, taaki galat photo par galat text na aaye. Agar jagah nahi hai toh warning dikhti hai.

**Q7. Is matcher ko aur smart kaise banaoge?**
CLIP jaise zero-shot image classifier se photo ko khud label karwana (kitchen/bedroom/etc.), phir wahi `match_score()` use karna. Synonyms ke liye word embeddings.

**Q8. LLM add karna ho toh kaise karoge?**
Template script ko baseline rakhunga. LLM ko sirf user ke facts dunga, "naya fact mat jodo" bolunga, output `check_grounding()` se guzaarunga, aur fail hone par template wapis. API key `.env` se, kabhi code mein nahi.

### Design decisions
**Q9. Pillow se text kyun, MoviePy TextClip se kyun nahi?**
TextClip ko ImageMagick ya font path chahiye, Windows par sabse zyada install problems yahin aati hain. Pillow + bundled font har PC par chalta hai.

**Q10. Video browser mein chale, iske liye kya kiya?**
H.264 (libx264) + `yuv420p` + `faststart`. Dono har browser aur phone support karte hain. Test mein ffmpeg se codec aur pixel format check hote hain.

**Q11. Template-based script robotic nahi lagegi?**
Haan, wording simple hai. Ye trade-off jaan-bujhkar hai: reliability > variety. Variety ke liye LLM future step hai, grounding check ke saath.

**Q12. 20-40 second ka target kaise ensure kiya?**
Har scene 4-5 second. 4 photos = ~21 sec, 8 photos = ~33 sec. Tests har count (4 se 8) ke liye length check karte hain.

**Q13. 4 photos aur 8 features ho toh?**
4 photos mein sirf 1 feature scene hota hai (max 3 features per photo). Baaki features invent ya cut-chhaant nahi hote, warning mein list hote hain ki "did not fit". Zyada photos ya kam labels se zyada features dikh sakte hain.

### Reliability and testing
**Q14. Galat ya corrupted image aaye toh?**
Pehle extension, phir Pillow se asli format, `verify()`, phir poori image load karke dekhte hain. Message mein file ka naam aur wajah aati hai. GIF ko .jpg rename karne se kaam nahi chalega.

**Q15. Export beech mein fail ho jaye toh?**
Video pehle `.part.mp4` mein banta hai, complete hone par hi rename hota hai. Fail par temp file delete hoti hai aur friendly message aata hai (disk full, file locked, memory). Test mein fail simulate karke verify kiya.

**Q16. Kya test kiya, aur kya nahi?**
102 tests: validation, script/facts-only, 2 real MP4 renders (codec, size, duration, last frame par CTA), UI flow. Nahi hua: Windows `run.bat` par test aur real Chrome/Edge playback (maine Linux par banaya, MP4 FFmpeg se decode hota hai).

**Q17. Memory aur speed?**
8 GB par chalega: images pehle hi resize hoti hain, 1280x720, 24 fps. 30 second video ~45-60 second mein banti hai (CPU encode). Fast karne ke liye: fps kam, hardware encoder (NVENC), ya background job queue.

**Q18. Security / privacy?**
Koi API key nahi, koi network call nahi, data local rehta hai. Upload par size (15 MB), pixels (40 MP) aur type limits hain. Streamlit telemetry band hai.

### Code
**Q19. Result `session_state` mein kyun?**
Streamlit har button click par script dobara chalata hai. Download button dabane par bhi video gayab na ho, isliye result `session_state` mein rakha.

**Q20. Scene aur image ka mapping kaise hota hai?**
Har photo ek scene. Scene i = photo i. Pehli photo hook, doosri intro, beech ki photos feature/fact scenes, aakhri closing. Isliye user ko photos order mein upload karni chahiye.

**Q21. Cross-fade kaise banaya?**
Har clip `duration + 0.8s` ka hota hai aur agle scene ke start par overlap hota hai, naye clip par `CrossFadeIn(0.8)`. Saath mein har photo par 6% slow zoom.

**Q22. Features comma se kaise split hote hain? "1,200 sq ft" toot jayega.**
Regex comma tab hi todta hai jab uske dono taraf digits na hon. Isliye "1,200 sq ft" ek feature rehta hai. Test hai.

### Limitations and future
**Q23. Kya missing hai?**
Narration audio aur background music (assignment mein optional). Voice-over sirf text mein hai. Photos ki content nahi samajhta (labels se kaam chalata hai). English templates.

**Q24. Aage kya karoge?**
(1) Offline TTS (pyttsx3) ya cloud voice, (2) licensed music, (3) CLIP se auto-labelling, (4) LLM caption rewrite with grounding guard, (5) batch mode for a listing sheet, (6) Hindi support (Devanagari font + templates).

### Honesty questions
**Q25. Ye code tumne khud likha?**
Seedha aur sach bolo. `DISCLOSURE.md` mein likha hai ki AI coding assistant (Claude) ki madad se bana. Tum bol sakte ho: "Maine AI assistant ki madad se banaya, requirements aur approach maine decide kiye, aur main har module samajhta hoon." Ye tabhi bolna jab ye sach ho, isliye aaj raat code padho (checklist ka step 2). Agar koi function na aaye toh bolo "main ye file dekh ke batata hoon" aur uska comment padh lo.

**Q26. Sabse badi kamzori kya hai?**
Video silent hai (narration nahi), aur photo-feature matching abhi manual labels par depend karti hai. Dono ka plan hai: TTS aur CLIP auto-labelling.

---

## 5. Live demo plan (3 minutes)
1. Empty form par **Generate video** dabao: friendly error list dikhao.
2. **Load sample property**: form, 7 photos aur photo labels bhar jaate hain.
3. **Generate video**: jab progress chale tab bolo: "script pehle banta hai, har photo ek scene, FFmpeg MP4 export karta hai."
4. Video chalao: hook, price, feature scenes (har feature sahi photo ke saath), enquiry prompt.
5. **Scene captions** table dikhao, phir **Download MP4**.
6. Ek label hatake (ya photo order badalke) dobara generate karo: dikhao ki "feature kaise sahi photo pe jaata hai."
7. Vertical 9:16 format (optional).

**Agar kuch fail ho:** shaant raho, `outputs/sample_property_video.mp4` chalao, aur batao ki ye isi app se bana hai.

## 6. Numbers to remember
| Cheez | Value |
|---|---|
| Photos | 4 to 8, JPG/PNG, max 15 MB, short side at least 400 px |
| Video | 1280x720 (or 720x1280), 24 fps, H.264, no audio |
| Length | 4-5 s per scene, about 21 s (4 photos) to 33 s (8 photos) |
| Transition | 0.8 s cross-fade, 6% slow zoom |
| Features per photo | max 3 |
| Tests | 102, includes real renders |
| Render time | about 45-60 s for 30 s video |
| Sample | 7 synthetic illustrations, fictional property, example.com contact |

## 7. Things NOT to claim
* Do not say it works on Windows "tested": say it was built and tested on Linux and you ran `run.bat` on your laptop (only if you actually did).
* Do not say it "understands" photos. It uses your labels.
* Do not call the grounding check "AI". It is a rule-based verifier.
* Do not say narration/music exist. They do not.

---

## 8. Update GitHub (PowerShell, inside the project folder)
1. Download the new zip I gave you and extract it to a **new** folder.
2. Copy everything from the new folder into your existing project folder, replacing files (keep your `.git` folder and `venv`).
3. Run:
```powershell
git add .
git commit -m "Match features to labelled photos, add tests and interview prep"
git push
```
