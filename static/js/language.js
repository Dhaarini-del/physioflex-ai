
/*
 * PhysioFlex Offline Multilingual Engine
 * Version: 1.0
 * No external translation API required.
 */

(() => {
    "use strict";

    const LANGUAGES = {
        en: "English",
        as: "অসমীয়া",
        bn: "বাংলা",
        brx: "बड़ो",
        doi: "डोगरी",
        gu: "ગુજરાતી",
        hi: "हिन्दी",
        kn: "ಕನ್ನಡ",
        ks: "कॉशुर",
        kok: "कोंकणी",
        mai: "मैथिली",
        ml: "മലയാളം",
        mni: "মৈতৈলোন",
        mr: "मराठी",
        ne: "नेपाली",
        or: "ଓଡ଼ିଆ",
        pa: "ਪੰਜਾਬੀ",
        sa: "संस्कृतम्",
        sat: "ᱥᱟᱱᱛᱟᱲᱤ",
        sd: "سنڌي",
        ta: "தமிழ்",
        te: "తెలుగు",
        ur: "اردو"
    };

    /*
     * Offline dictionaries.
     * English is the fallback language.
     * Add translations using the same English keys.
     */

    const DICTIONARY = {
        en: {
            "Dashboard": "Dashboard",
            "Patients": "Patients",
            "Doctors": "Doctors",
            "Physiotherapists": "Physiotherapists",
            "Appointments": "Appointments",
            "Exercises": "Exercises",
            "Reports": "Reports",
            "Notifications": "Notifications",
            "Settings": "Settings",
            "Profile": "Profile",
            "Logout": "Logout",
            "Login": "Login",
            "Register": "Register",
            "Save": "Save",
            "Cancel": "Cancel",
            "Search": "Search",
            "Language": "Language",
            "Welcome": "Welcome",
            "Loading...": "Loading...",
            "Submit": "Submit",
            "Home": "Home",
            "Patient Dashboard": "Patient Dashboard",
            "Doctor Dashboard": "Doctor Dashboard",
            "Physiotherapist Dashboard": "Physiotherapist Dashboard",
            "signout": "Sign out",
            "my_recovery": "My Recovery Journey",
            "alert_clinician": "Alert Care Team",
            "book_live": "Book Live Session",
            "voice_msg": "Voice Note",
            "pain": "Pain Level",
            "adherence": "Adherence",
            "eval_score": "Clinical Score",
            "assigned_ex": "Prescribed Exercises – Select to Begin",
            "no_plan": "No active plan yet. Wait for your physiotherapist to assign exercises.",
            "schedules": "Schedules & Hospital Visits",
            "progress_eval": "Clinical Progress Evaluation",
            "recent_sessions": "Recent Workout Sessions",
            "start": "Start Exercise 🏃"
        },

        hi: {
            "Dashboard": "डैशबोर्ड",
            "Patients": "मरीज़",
            "Doctors": "डॉक्टर",
            "Physiotherapists": "फिजियोथेरेपिस्ट",
            "Appointments": "अपॉइंटमेंट",
            "Exercises": "व्यायाम",
            "Reports": "रिपोर्ट",
            "Notifications": "सूचनाएं",
            "Settings": "सेटिंग्स",
            "Profile": "प्रोफ़ाइल",
            "Logout": "लॉग आउट",
            "Login": "लॉगिन",
            "Register": "पंजीकरण",
            "Save": "सहेजें",
            "Cancel": "रद्द करें",
            "Search": "खोजें",
            "Language": "भाषा",
            "Welcome": "स्वागत है",
            "Loading...": "लोड हो रहा है...",
            "Submit": "जमा करें",
            "Home": "होम",
            "Patient Dashboard": "मरीज़ डैशबोर्ड",
            "Doctor Dashboard": "डॉक्टर डैशबोर्ड",
            "Physiotherapist Dashboard": "फिजियोथेरेपिस्ट डैशबोर्ड",
            "signout": "साइन आउट",
            "my_recovery": "मेरी रिकवरी यात्रा",
            "alert_clinician": "केयर टीम अलर्ट",
            "book_live": "लाइव सत्र बुक करें",
            "voice_msg": "वॉइस संदेश",
            "pain": "दर्द का स्तर",
            "adherence": "अनुपालन",
            "eval_score": "मूल्यांकन स्कोर",
            "assigned_ex": "नियत व्यायाम – शुरू करने के लिए चुनें",
            "no_plan": "कोई सक्रिय योजना नहीं है।",
            "schedules": "अनुसूची और विज़िट",
            "progress_eval": "प्रगति मूल्यांकन",
            "recent_sessions": "हाल के सत्र",
            "start": "व्यायाम शुरू करें 🏃"
        },

        ta: {
            "Dashboard": "முகப்புப் பலகை",
            "Patients": "நோயாளிகள்",
            "Doctors": "மருத்துவர்கள்",
            "Physiotherapists": "பிசியோதெரபிஸ்ட்கள்",
            "Appointments": "சந்திப்புகள்",
            "Exercises": "உடற்பயிற்சிகள்",
            "Reports": "அறிக்கைகள்",
            "Notifications": "அறிவிப்புகள்",
            "Settings": "அமைப்புகள்",
            "Profile": "சுயவிவரம்",
            "Logout": "வெளியேறு",
            "Login": "உள்நுழை",
            "Register": "பதிவு செய்",
            "Save": "சேமி",
            "Cancel": "ரத்துசெய்",
            "Search": "தேடு",
            "Language": "மொழி",
            "Welcome": "வரவேற்கிறோம்",
            "Loading...": "ஏற்றப்படுகிறது...",
            "Submit": "சமர்ப்பி",
            "Home": "முகப்பு",
            "Patient Dashboard": "நோயாளர் முகப்புப் பலகை",
            "Doctor Dashboard": "மருத்துவர் முகப்புப் பலகை",
            "Physiotherapist Dashboard": "பிசியோதெரபிஸ்ட் முகப்புப் பலகை",
            "signout": "வெளியேறு",
            "my_recovery": "எனது குணமடைதல் பயணம்",
            "alert_clinician": "சிகிச்சைக் குழுவை எச்சரி",
            "book_live": "நேரடி அமர்வை முன்பதிவு செய்",
            "voice_msg": "குரல் குறிப்பு",
            "pain": "வலி நிலை",
            "adherence": "முறையாகப் பின்பற்றுதல்",
            "eval_score": "மருத்துவ மதிப்பீடு",
            "assigned_ex": "பரிந்துரைக்கப்பட்ட பயிற்சிகள் – தொடங்கத் தேர்ந்தெடுக்கவும்",
            "no_plan": "இன்னும் செயலில் உள்ள திட்டம் இல்லை.",
            "schedules": "அட்டவணைகள் மற்றும் மருத்துவமனை வருகைகள்",
            "progress_eval": "மருத்துவ முன்னேற்ற மதிப்பீடு",
            "recent_sessions": "சமீபத்திய உடற்பயிற்சி அமர்வுகள்",
            "start": "பயிற்சியைத் தொடங்கு 🏃"
        },

        kn: {
            "Dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
            "Patients": "ರೋಗಿಗಳು",
            "Doctors": "ವೈದ್ಯರು",
            "Physiotherapists": "ಭೌತಚಿಕಿತ್ಸಕರು",
            "Appointments": "ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್‌ಗಳು",
            "Exercises": "ವ್ಯಾಯಾಮಗಳು",
            "Reports": "ವರದಿಗಳು",
            "Notifications": "ಅಧಿಸೂಚನೆಗಳು",
            "Settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
            "Profile": "ಪ್ರೊಫೈಲ್",
            "Logout": "ಲಾಗ್ ಔಟ್",
            "Login": "ಲಾಗಿನ್",
            "Register": "ನೋಂದಣಿ",
            "Save": "ಉಳಿಸಿ",
            "Cancel": "ರದ್ದುಮಾಡಿ",
            "Search": "ಹುಡುಕಿ",
            "Language": "ಭಾಷೆ",
            "Welcome": "ಸ್ವಾಗತ",
            "Loading...": "ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
            "Submit": "ಸಲ್ಲಿಸಿ",
            "Home": "ಮುಖಪುಟ",
            "Patient Dashboard": "ರೋಗಿ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
            "Doctor Dashboard": "ವೈದ್ಯರ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
            "Physiotherapist Dashboard": "ಭೌತಚಿಕಿತ್ಸಕರ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
            "signout": "ಲಾಗ್ ಔಟ್",
            "my_recovery": "ನನ್ನ ಚೇತರಿಕೆಯ ಪಯಣ",
            "alert_clinician": "ಆರೈಕೆ ತಂಡವನ್ನು ಎಚ್ಚರಿಸಿ",
            "book_live": "ಲೈವ್ ಸೆಶನ್ ಬುಕ್ ಮಾಡಿ",
            "voice_msg": "ಧ್ವನಿ ಟಿಪ್ಪಣಿ",
            "pain": "ನೋವಿನ ಮಟ್ಟ",
            "adherence": "ಅನುಸರಣೆ",
            "eval_score": "ಕ್ಲಿನಿಕಲ್ ಸ್ಕೋರ್",
            "assigned_ex": "ನಿಯೋಜಿತ ವ್ಯಾಯಾಮಗಳು – ಪ್ರಾರಂಭಿಸಲು ಆಯ್ಕೆಮಾಡಿ",
            "no_plan": "ಇನ್ನೂ ಯಾವುದೇ ಸಕ್ರಿಯ ಯೋಜನೆ ನಿಯೋಜಿಸಲಾಗಿಲ್ಲ.",
            "schedules": "ವೇಳಾಪಟ್ಟಿಗಳು ಮತ್ತು ಆಸ್ಪತ್ರೆ ಭೇಟಿಗಳು",
            "progress_eval": "ಕ್ಲಿನಿಕಲ್ ಪ್ರಗತಿ ಮೌಲ್ಯಮಾಪನ",
            "recent_sessions": "ಇತ್ತೀಚಿನ ತಾಲೀಮು ಅವಧಿಗಳು",
            "start": "ವ್ಯಾಯಾಮ ಪ್ರಾರಂಭಿಸಿ 🏃"
        },

        te: {
            "Dashboard": "డాష్‌బోర్డ్",
            "Patients": "రోగులు",
            "Doctors": "వైద్యులు",
            "Physiotherapists": "ఫిజియోథెరపిస్టులు",
            "Appointments": "అపాయింట్‌మెంట్‌లు",
            "Exercises": "వ్యాయామాలు",
            "Reports": "నివేదికలు",
            "Notifications": "నోటిఫికేషన్‌లు",
            "Settings": "సెట్టింగ్‌లు",
            "Profile": "ప్రొఫైల్",
            "Logout": "లాగ్ అవుట్",
            "Login": "లాగిన్",
            "Register": "నమోదు",
            "Save": "సేవ్ చేయండి",
            "Cancel": "రద్దు చేయండి",
            "Search": "వెతకండి",
            "Language": "భాష",
            "Welcome": "స్వాగతం",
            "Loading...": "లోడ్ అవుతోంది...",
            "Submit": "సమర్పించండి",
            "Home": "హోమ్",
            "Patient Dashboard": "రోగి డాష్‌బోర్డ్",
            "Doctor Dashboard": "వైద్యుల డాష్‌బోర్డ్",
            "Physiotherapist Dashboard": "ఫిజియోథెరపిస్ట్ డాష్‌బోర్డ్",
            "signout": "లాగ్ అవుట్",
            "my_recovery": "నా రికవరీ ప్రయాణం",
            "alert_clinician": "కేర్ టీమ్‌ను అప్రమత్తం చేయండి",
            "book_live": "లైవ్ సెషన్ బుక్ చేసుకోండి",
            "voice_msg": "వాయిస్ నోట్",
            "pain": "నొప్పి స్థాయి",
            "adherence": "నిబద్ధత",
            "eval_score": "క్లినికల్ స్కోర్",
            "assigned_ex": "సూచించిన వ్యాయామాలు – ప్రారంభించడానికి ఎంచుకోండి",
            "no_plan": "ఇంకా క్రియాశీల ప్రణాళిక కేటాయించబడలేదు.",
            "schedules": "షెడ్యూల్‌లు మరియు ఆసుపత్రి సందర్శనలు",
            "progress_eval": "క్లినికల్ పురోగతి మూల్యాంకనం",
            "recent_sessions": "ఇటీవలి వ్యాయామ సెషన్‌లు",
            "start": "వ్యాయామం ప్రారంభించండి 🏃"
        },

        ml: {
            "Dashboard": "ഡാഷ്ബോർഡ്",
            "Patients": "രോഗികൾ",
            "Doctors": "ഡോക്ടർമാർ",
            "Physiotherapists": "ഫിസിയോതെറാപ്പിസ്റ്റുകൾ",
            "Appointments": "അപ്പോയിന്റ്മെന്റുകൾ",
            "Exercises": "വ്യായാമങ്ങൾ",
            "Reports": "റിപ്പോർട്ടുകൾ",
            "Notifications": "അറിയിപ്പുകൾ",
            "Settings": "ക്രമീകരണങ്ങൾ",
            "Profile": "പ്രൊഫൈൽ",
            "Logout": "ലോഗ് ഔട്ട്",
            "Login": "ലോഗിൻ",
            "Register": "രജിസ്റ്റർ",
            "Save": "സംരക്ഷിക്കുക",
            "Cancel": "റദ്ദാക്കുക",
            "Search": "തിരയുക",
            "Language": "ഭാഷ",
            "Welcome": "സ്വാഗതം",
            "Loading...": "ലോഡ് ചെയ്യുന്നു...",
            "Submit": "സമർപ്പിക്കുക",
            "Home": "ഹോം",
            "Patient Dashboard": "രോഗിയുടെ ഡാഷ്ബോർഡ്",
            "Doctor Dashboard": "ഡോക്ടറുടെ ഡാഷ്ബോർഡ്",
            "Physiotherapist Dashboard": "ഫിസിയോതെറാപ്പിസ്റ്റിന്റെ ഡാഷ്ബോർഡ്",
            "signout": "ലോഗ് ഔട്ട്",
            "my_recovery": "എന്റെ വീണ്ടെടുക്കൽ യാത്ര",
            "alert_clinician": "കെയർ ടീമിനെ അറിയിക്കുക",
            "book_live": "തത്സമയ സെഷൻ ബുക്ക് ചെയ്യുക",
            "voice_msg": "വോയ്‌സ് നോട്ട്",
            "pain": "വേദനയുടെ അളവ്",
            "adherence": "തുടർച്ച",
            "eval_score": "ക്ലിനിക്കൽ സ്കോർ",
            "assigned_ex": "നിർദ്ദേശിച്ച വ്യായാമങ്ങൾ – ആരംഭിക്കാൻ തിരഞ്ഞെടുക്കുക",
            "no_plan": "ഇതുവരെ സജീവമായ പ്ലാൻ നൽകിയിട്ടില്ല.",
            "schedules": "ഷെഡ്യൂളുകളും ആശുപത്രി സന്ദർശനങ്ങളും",
            "progress_eval": "ക്ലിനിക്കൽ പുരോഗതി വിലയിരുത്തൽ",
            "recent_sessions": "സമീപകാല വ്യായാമ സെഷനുകൾ",
            "start": "വ്യായാമം ആരംഭിക്കുക 🏃"
        },

        bn: {
            "Dashboard": "ড্যাশবোর্ড",
            "Patients": "রোগীরা",
            "Doctors": "চিকিৎসক",
            "Appointments": "অ্যাপয়েন্টমেন্ট",
            "Exercises": "ব্যায়াম",
            "Reports": "রিপোর্ট",
            "Notifications": "বিজ্ঞপ্তি",
            "Settings": "সেটিংস",
            "Profile": "প্রোফাইল",
            "Logout": "লগ আউট",
            "Login": "লগইন",
            "Register": "নিবন্ধন",
            "Save": "সংরক্ষণ করুন",
            "Cancel": "বাতিল",
            "Search": "অনুসন্ধান",
            "Language": "ভাষা",
            "Welcome": "স্বাগতম",
            "Home": "হোম",
            "signout": "সাইন আউট",
            "my_recovery": "আমার সুস্থতার যাত্রা",
            "alert_clinician": "কেয়ার টিমকে সতর্ক করুন",
            "book_live": "সরাসরি সেশন বুক করুন",
            "voice_msg": "ভয়েস নোট",
            "pain": "ব্যথার মাত্রা",
            "adherence": "নিয়মিততা",
            "eval_score": "ক্লিনিক্যাল স্কোর",
            "assigned_ex": "নির্ধারিত ব্যায়াম – শুরু করতে নির্বাচন করুন",
            "no_plan": "এখনও কোনও সক্রিয় পরিকল্পনা বরাদ্দ করা হয়নি।",
            "schedules": "সময়সূচী এবং হাসপাতালে পরিদর্শন",
            "progress_eval": "ক্লিনিক্যাল অগ্রগতি মূল্যায়ন",
            "recent_sessions": "সাম্প্রতিক ব্যায়াম সেশন",
            "start": "ব্যায়াম শুরু করুন 🏃"
        },

        mr: {
            "Dashboard": "डॅशबोर्ड",
            "Patients": "रुग्ण",
            "Doctors": "डॉक्टर",
            "Appointments": "भेटी",
            "Exercises": "व्यायाम",
            "Reports": "अहवाल",
            "Notifications": "सूचना",
            "Settings": "सेटिंग्ज",
            "Profile": "प्रोफाइल",
            "Logout": "बाहेर पडा",
            "Login": "लॉगिन",
            "Register": "नोंदणी",
            "Save": "जतन करा",
            "Cancel": "रद्द करा",
            "Search": "शोधा",
            "Language": "भाषा",
            "Welcome": "स्वागत आहे",
            "Home": "मुख्यपृष्ठ",
            "signout": "साइन आउट",
            "my_recovery": "माझा बरे होण्याचा प्रवास",
            "alert_clinician": "केअर टीमला सतर्क करा",
            "book_live": "थेट सत्र बुक करा",
            "voice_msg": "व्हॉइस टीप",
            "pain": "वेदनेची पातळी",
            "adherence": "नियमितता",
            "eval_score": "क्लिनिकल स्कोअर",
            "assigned_ex": "नेमून दिलेले व्यायाम – सुरू करण्यासाठी निवडा",
            "no_plan": "अद्याप कोणतीही सक्रिय योजना नियुक्त केलेली नाही.",
            "schedules": "वेळापत्रक आणि रुग्णालयाच्या भेटी",
            "progress_eval": "क्लिनिकल प्रगती मूल्यांकन",
            "recent_sessions": "अलीकडील व्यायाम सत्रे",
            "start": "व्यायाम सुरू करा 🏃"
        },

        gu: {
            "Dashboard": "ડેશબોર્ડ",
            "Patients": "દર્દીઓ",
            "Doctors": "ડૉક્ટરો",
            "Appointments": "મુલાકાતો",
            "Exercises": "કસરતો",
            "Reports": "અહેવાલો",
            "Notifications": "સૂચનાઓ",
            "Settings": "સેટિંગ્સ",
            "Profile": "પ્રોફાઇલ",
            "Logout": "લૉગ આઉટ",
            "Login": "લૉગિન",
            "Register": "નોંધણી",
            "Save": "સાચવો",
            "Cancel": "રદ કરો",
            "Search": "શોધો",
            "Language": "ભાષા",
            "Welcome": "સ્વાગત છે",
            "Home": "હોમ",
            "signout": "સાઇન આઉટ",
            "my_recovery": "મારી સ્વસ્થતા યાત્રા",
            "alert_clinician": "સંભાળ ટીમને ચેતવણી આપો",
            "book_live": "લાઇવ સત્ર બુક કરો",
            "voice_msg": "વૉઇસ નોંધ",
            "pain": "પીડા સ્તર",
            "adherence": "નિયમિતતા",
            "eval_score": "ક્લિનિકલ સ્કોર",
            "assigned_ex": "સોંપેલ કસરતો – શરૂ કરવા માટે પસંદ કરો",
            "no_plan": "હજી સુધી કોઈ સક્રિય યોજના સોંપવામાં આવી નથી.",
            "schedules": "સમયપત્રક અને હોસ્પિટલ મુલાકાતો",
            "progress_eval": "ક્લિનિકલ પ્રગતિ મૂલ્યાંકન",
            "recent_sessions": "તાજેતરના કસરત સત્રો",
            "start": "કસરત શરૂ કરો 🏃"
        },

        pa: {
            "Dashboard": "ਡੈਸ਼ਬੋਰਡ",
            "Patients": "ਮਰੀਜ਼",
            "Doctors": "ਡਾਕਟਰ",
            "Appointments": "ਮੁਲਾਕਾਤਾਂ",
            "Exercises": "ਕਸਰਤਾਂ",
            "Reports": "ਰਿਪੋਰਟਾਂ",
            "Notifications": "ਸੂਚਨਾਵਾਂ",
            "Settings": "ਸੈਟਿੰਗਾਂ",
            "Profile": "ਪ੍ਰੋਫਾਈਲ",
            "Logout": "ਲੌਗ ਆਉਟ",
            "Login": "ਲੌਗਇਨ",
            "Register": "ਰਜਿਸਟਰ",
            "Save": "ਸੰਭਾਲੋ",
            "Cancel": "ਰੱਦ ਕਰੋ",
            "Search": "ਖੋਜੋ",
            "Language": "ਭਾਸ਼ਾ",
            "Welcome": "ਜੀ ਆਇਆਂ ਨੂੰ",
            "Home": "ਮੁੱਖ ਪੰਨਾ",
            "signout": "ਸਾਈਨ ਆਉਟ",
            "my_recovery": "ਮੇਰਾ ਰਿਕਵਰੀ ਸਫ਼ਰ",
            "alert_clinician": "ਕੇਅਰ ਟੀਮ ਨੂੰ ਸੁਚੇਤ ਕਰੋ",
            "book_live": "ਲਾਈਵ ਸੈਸ਼ਨ ਬੁੱਕ ਕਰੋ",
            "voice_msg": "ਵੌਇਸ ਨੋਟ",
            "pain": "ਦਰਦ ਦਾ ਪੱਧਰ",
            "adherence": "ਨਿਰੰਤਰਤਾ",
            "eval_score": "ਕਲੀਨਿਕਲ ਸਕੋਰ",
            "assigned_ex": "ਨਿਰਧਾਰਤ ਕਸਰਤਾਂ – ਸ਼ੁਰੂ ਕਰਨ ਲਈ ਚੁਣੋ",
            "no_plan": "ਅਜੇ ਕੋਈ ਸਰਗਰਮ ਯੋਜਨਾ ਨਿਰਧਾਰਤ ਨਹੀਂ ਕੀਤੀ ਗਈ।",
            "schedules": "ਸਮਾਂ-ਸਾਰਣੀ ਅਤੇ ਹਸਪਤਾਲ ਦੇ ਦੌਰੇ",
            "progress_eval": "ਕਲੀਨਿਕਲ ਪ੍ਰਗਤੀ ਮੁਲਾਂਕਣ",
            "recent_sessions": "ਤਾਜ਼ਾ ਕਸਰਤ ਸੈਸ਼ਨ",
            "start": "ਕਸਰਤ ਸ਼ੁਰੂ ਕਰੋ 🏃"
        },

        ur: {
            "Dashboard": "ڈیش بورڈ",
            "Patients": "مریض",
            "Doctors": "ڈاکٹرز",
            "Appointments": "ملاقاتیں",
            "Exercises": "ورزشیں",
            "Reports": "رپورٹس",
            "Notifications": "اطلاعات",
            "Settings": "ترتیبات",
            "Profile": "پروفائل",
            "Logout": "لاگ آؤٹ",
            "Login": "لاگ ان",
            "Register": "رجسٹر",
            "Save": "محفوظ کریں",
            "Cancel": "منسوخ کریں",
            "Search": "تلاش کریں",
            "Language": "زبان",
            "Welcome": "خوش آمدید",
            "Home": "ہوم",
            "signout": "لاگ آؤٹ",
            "my_recovery": "میری بحالی کا سفر",
            "alert_clinician": "کیئر ٹیم کو مطلع کریں",
            "book_live": "لائیو سیشن بک کریں",
            "voice_msg": "صوتی نوٹ",
            "pain": "درد کی شدت",
            "adherence": "پابندی",
            "eval_score": "کلینیکل اسکور",
            "assigned_ex": "تجویز کردہ ورزشیں – شروع کرنے کے لیے منتخب کریں",
            "no_plan": "ابھی تک کوئی فعال منصوبہ تفویض نہیں کیا گیا ہے۔",
            "schedules": "شیڈول اور ہسپتال کے دورے",
            "progress_eval": "کلینیکل پیش رفت کا جائزہ",
            "recent_sessions": "حالیہ ورزش کے سیشن",
            "start": "ورزش شروع کریں 🏃"
        },

        // These languages are registered and selectable.
        // Their translations can be added using the same keys.
        as: {},
        brx: {},
        doi: {},
        ks: {},
        kok: {},
        mai: {},
        mni: {},
        ne: {},
        or: {},
        sa: {},
        sat: {},
        sd: {}
    };

    const STORAGE_KEY = "physioflex_language";
    const RTL_LANGUAGES = ["ur", "ks", "sd"];

    let currentLanguage = "en";
    const originalValues = new WeakMap();

    function getDictionary(language) {
        return DICTIONARY[language] || DICTIONARY.en;
    }

    function translateText(value, language) {
        const dictionary = getDictionary(language);
        const trimmed = value.trim();

        if (!trimmed) return value;

        const translated = dictionary[trimmed];

        if (translated === undefined) return value;

        return value.replace(trimmed, translated);
    }

    function translateElement(element, language) {
        if (!element || element.nodeType !== 1) return;

        // Explicit translation keys take priority.
        if (element.hasAttribute("data-i18n")) {
            const key = element.getAttribute("data-i18n");

            if (!originalValues.has(element)) {
                originalValues.set(element, {
                    text: element.textContent
                });
            }

            const translated = getDictionary(language)[key];

            if (translated !== undefined) {
                element.textContent = translated;
            } else if (language === "en") {
                element.textContent = key;
            }
        }

        // Translate placeholders.
        if (element.hasAttribute("data-i18n-placeholder")) {
            const key = element.getAttribute("data-i18n-placeholder");
            const translated = getDictionary(language)[key];

            if (translated !== undefined) {
                element.setAttribute("placeholder", translated);
            }
        }

        // Translate titles and accessibility labels.
        ["title", "aria-label"].forEach(attribute => {
            const keyAttribute = "data-i18n-" + attribute;

            if (element.hasAttribute(keyAttribute)) {
                const key = element.getAttribute(keyAttribute);
                const translated = getDictionary(language)[key];

                if (translated !== undefined) {
                    element.setAttribute(attribute, translated);
                }
            }
        });

        // Translate ordinary text nodes without replacing HTML elements.
        for (const node of element.childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                if (!originalValues.has(node)) {
                    originalValues.set(node, node.nodeValue);
                }

                const original = originalValues.get(node);
                node.nodeValue = translateText(original, language);
            }
        }

        // Translate descendant elements.
        element.querySelectorAll("*").forEach(child => {
            if (child.hasAttribute("data-i18n")) {
                translateElement(child, language);
            } else {
                for (const node of child.childNodes) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        if (!originalValues.has(node)) {
                            originalValues.set(node, node.nodeValue);
                        }

                        const original = originalValues.get(node);
                        node.nodeValue = translateText(original, language);
                    }
                }
            }

            ["placeholder", "title", "aria-label"].forEach(attribute => {
                const keyAttribute = "data-i18n-" + attribute;

                if (child.hasAttribute(keyAttribute)) {
                    const key = child.getAttribute(keyAttribute);
                    const translated = getDictionary(language)[key];

                    if (translated !== undefined) {
                        child.setAttribute(attribute, translated);
                    }
                }
            });
        });
    }

    function applyLanguage(language) {
        if (!LANGUAGES[language]) {
            language = "en";
        }

        currentLanguage = language;

        document.documentElement.lang = language;
        document.documentElement.dir =
            RTL_LANGUAGES.includes(language) ? "rtl" : "ltr";

        document.documentElement.classList.add("multilingual-font");

        const root = document.body;

        if (root) {
            translateElement(root, language);
        }

        const selector = document.getElementById("language-selector");

        if (selector) {
            selector.value = language;
        }

        try {
            localStorage.setItem(STORAGE_KEY, language);
        } catch (error) {
            console.warn("Could not save language preference", error);
        }

        document.dispatchEvent(
            new CustomEvent("physioflex:languageChanged", {
                detail: {
                    language,
                    languageName: LANGUAGES[language]
                }
            })
        );

        console.info("[PhysioFlex] Language selected:", language);
    }

    function initializeLanguage() {
        const selector = document.getElementById("language-selector");

        let savedLanguage = "en";

        try {
            savedLanguage = localStorage.getItem(STORAGE_KEY) || localStorage.getItem("lang") || "en";
        } catch (error) {
            console.warn("Language storage unavailable", error);
        }

        if (!LANGUAGES[savedLanguage]) {
            savedLanguage = "en";
        }

        if (selector) {
            selector.addEventListener("change", event => {
                applyLanguage(event.target.value);
            });
        }

        applyLanguage(savedLanguage);

        // Support content added later by dashboard JavaScript.
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        translateElement(node, currentLanguage);
                    } else if (node.nodeType === Node.TEXT_NODE) {
                        if (!originalValues.has(node)) {
                            originalValues.set(node, node.nodeValue);
                        }

                        node.nodeValue = translateText(
                            originalValues.get(node),
                            currentLanguage
                        );
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Public interface for other PhysioFlex scripts.
    window.PhysioFlexI18n = {
        languages: LANGUAGES,
        dictionary: DICTIONARY,
        setLanguage: applyLanguage,
        getLanguage: () => currentLanguage,
        translate: (key) => getDictionary(currentLanguage)[key] || key,
        addTranslations: (language, translations) => {
            if (!DICTIONARY[language]) {
                DICTIONARY[language] = {};
            }

            Object.assign(DICTIONARY[language], translations);
            applyLanguage(currentLanguage);
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeLanguage);
    } else {
        initializeLanguage();
    }
})();
