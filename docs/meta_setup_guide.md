# ফেসবুক (Meta) অ্যাডস ইন্টিগ্রেশন ও লাইভ রানিং গাইড

আপনার ফেসবুক অ্যাকাউন্টে এই অটোনোমাস এজেন্টের মাধ্যমে রিয়েল অ্যাড রান ও পরিচালনা করার জন্য নিচের ৪টি সহজ ধাপ অনুসরণ করুন:

---

### ধাপ ১: প্রয়োজনীয় ২টি তথ্য সংগ্রহ করুন
১. **Meta Ad Account ID**:
   - আপনার ফেসবুক [Ads Manager](https://adsmanager.facebook.com)-এ যান।
   - উপরের বাম কোণে ড্রপডাউন থেকে আপনার অ্যাকাউন্ট নম্বরটি দেখুন (যেমন: `act_123456789012345` বা শুধু নম্বরটি)।
২. **Meta Access Token**:
   - [developers.facebook.com](https://developers.facebook.com)-এ যান।
   - একটি App তৈরি করুন (Type: `Business`) এবং **Marketing API** যোগ করুন।
   - **Graph API Explorer** অথবা **System Users** (Meta Business Suite -> Settings -> System Users) থেকে একটি Access Token তৈরি করুন।
   - প্রয়োজনীয় পারমিশন: `ads_read`, `ads_management`, `business_management`।

---

### ধাপ ২: স্বয়ংক্রিয় অনবোর্ডিং স্ক্রিপ্ট চালানো
টার্মিনালে সরাসরি নিচের কমান্ডটি চালান:
```bash
.\.venv\Scripts\python.exe scripts/onboard_client.py
```
এই স্ক্রিপ্টটি আপনার দেওয়া টোকেনটি সরাসরি মেটা গ্রাফ এপিআই দিয়ে টেস্ট করবে এবং সফল হলে নিরাপদে `.env` ও `config/clients.yaml`-এ কনফিগার করে দেবে।

---

### ধাপ ৩: লাইভ ডেটা অডিট ও যাচাই (Read-Only Mode)
অ্যাকাউন্টে কোনো পরিবর্তন বা টাকা কাটার আগেই এজেন্টকে আপনার অ্যাকাউন্টের লাইভ ডেটা পড়তে দিন:
```bash
.\.venv\Scripts\python.exe -m agency_engine.cli audit --client my_brand --mode read_only
```
- এজেন্ট আপনার সমস্ত রানিং ক্যাম্পেইন, স্পেন্ড, ক্লিক ও কনভার্সন এনালাইজ করবে।
- কোন ক্যাম্পেইনে বেশি টাকা অপচয় হচ্ছে বা সিপিএ বেশি তা অ্যানোমালি হিসেবে চিহ্নিত করবে।

---

### ধাপ ৪: এক্সিকিউটিভ ব্রিফিং দেখা
```bash
.\.venv\Scripts\python.exe -m agency_engine.cli brief --client my_brand --dry-run
```
আপনার ফেসবুক অ্যাকাউন্টের সম্পূর্ণ রিয়েল স্পেন্ড, কনভার্সন এবং সিপিএ রিপোর্ট দেখতে পাবেন।

---

### ধাপ ৫: অপটিমাইজেশন ও বাজেট কন্ট্রোল (Bounded Autonomy)
- **পজ / বাজেট বৃদ্ধি অনুমোদন**: এজেন্ট কোনো লস-মেকিং ক্যাম্পেইন পজ করতে চাইলে বা ভালো ক্যাম্পেইনে বাজেট বাড়ানোর সুপারিশ করলে তা প্রপোজাল আকারে জমা হয়।
- আপনি সিএলআই বা অনুমোদিত টেলিগ্রাম চ্যাট দিয়ে এক ক্লিকে অনুমোদন (`approve`) করতে পারবেন:
```bash
.\.venv\Scripts\python.exe -m agency_engine.cli approve --action-id <action_id> --approver "Human Operator"
```
- কোনো ভুল হলে মুহূর্তের মধ্যে রোলব্যাক করা যায়:
```bash
.\.venv\Scripts\python.exe -m agency_engine.cli rollback --action-id <action_id>
```
