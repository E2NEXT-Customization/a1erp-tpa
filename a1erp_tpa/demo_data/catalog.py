"""Pools of realistic (fictional) Iraqi data used by the demo data generator.

Every person, company, hospital and bank here is invented. Names follow Iraqi usage
(first name, father, grandfather, family name) and come with an Arabic and a Latin spelling."""

MALE = [
	("محمد", "Mohammed"), ("علي", "Ali"), ("حسين", "Hussein"), ("أحمد", "Ahmed"), ("حسن", "Hassan"), ("عباس", "Abbas"),
	("مصطفى", "Mustafa"), ("كرار", "Karrar"), ("حيدر", "Haider"), ("عمر", "Omar"), ("يوسف", "Yousif"), ("زيد", "Zaid"),
	("مرتضى", "Murtadha"), ("سجاد", "Sajjad"), ("أمير", "Ameer"), ("علاء", "Alaa"), ("فلاح", "Falah"), ("رعد", "Raad"),
	("ضياء", "Dhiaa"), ("صادق", "Sadiq"), ("جعفر", "Jaafar"), ("باسم", "Basim"), ("قاسم", "Qasim"), ("سامر", "Samer"),
	("منتظر", "Muntadhar"), ("أيمن", "Ayman"), ("ليث", "Laith"), ("وسام", "Wisam"), ("نبيل", "Nabeel"), ("ماجد", "Majid"),
	("إبراهيم", "Ibrahim"), ("خالد", "Khalid"), ("طه", "Taha"), ("بلال", "Bilal"), ("سيف", "Saif"), ("عثمان", "Othman"),
]
KURDISH_MALE = [("شوان", "Shwan"), ("كاروان", "Karwan"), ("ريبوار", "Rebwar"), ("دلشاد", "Dilshad"), ("هاوري", "Hawre"), ("آزاد", "Azad"),
	("سرهنك", "Sarhang"), ("بختيار", "Bakhtiyar")]
FEMALE = [
	("فاطمة", "Fatima"), ("زينب", "Zainab"), ("مريم", "Maryam"), ("نور", "Noor"), ("سارة", "Sara"), ("رقية", "Ruqaya"),
	("زهراء", "Zahraa"), ("هدى", "Huda"), ("آية", "Aya"), ("دعاء", "Duaa"), ("شهد", "Shahad"), ("رسل", "Rusul"),
	("غدير", "Ghadeer"), ("إسراء", "Israa"), ("بنين", "Baneen"), ("ملاك", "Malak"), ("حوراء", "Hawraa"), ("سجى", "Saja"),
	("ضحى", "Dhuha"), ("أسيل", "Aseel"), ("تبارك", "Tabarak"), ("هبة", "Hiba"), ("رنا", "Rana"), ("ميس", "Mays"),
]
KURDISH_FEMALE = [("شيلان", "Shilan"), ("نركز", "Nergiz"), ("آفين", "Avin"), ("هيرو", "Hero"), ("بيان", "Bayan")]
FATHERS = MALE + [
	("كاظم", "Kadhim"), ("جاسم", "Jasim"), ("كريم", "Kareem"), ("عبد الله", "Abdullah"), ("عبد الأمير", "Abdulameer"), ("صالح", "Salih"),
	("مهدي", "Mahdi"), ("جواد", "Jawad"), ("رحيم", "Raheem"), ("ناصر", "Nasir"), ("فاضل", "Fadhil"), ("طارق", "Tariq"),
	("ستار", "Sattar"), ("جبار", "Jabbar"), ("عدنان", "Adnan"), ("نعمة", "Nima"), ("هادي", "Hadi"), ("حميد", "Hameed"),
]
FAMILIES = [
	("الساعدي", "Al-Saadi"), ("الجبوري", "Al-Jubouri"), ("التميمي", "Al-Tamimi"), ("العبيدي", "Al-Obaidi"), ("الدليمي", "Al-Dulaimi"),
	("الربيعي", "Al-Rubaie"), ("الخفاجي", "Al-Khafaji"), ("الموسوي", "Al-Mousawi"), ("الحسيني", "Al-Husseini"), ("الزبيدي", "Al-Zubaidi"),
	("الكعبي", "Al-Kaabi"), ("الشمري", "Al-Shammari"), ("العزاوي", "Al-Azzawi"), ("الجنابي", "Al-Janabi"), ("البياتي", "Al-Bayati"),
	("السامرائي", "Al-Samarrai"), ("الحلي", "Al-Hilli"), ("الكبيسي", "Al-Kubaisi"), ("الأسدي", "Al-Asadi"), ("الطائي", "Al-Taie"),
	("العامري", "Al-Amiri"), ("الحمداني", "Al-Hamdani"), ("اللامي", "Al-Lami"), ("الفتلاوي", "Al-Fatlawi"), ("البصري", "Al-Basri"),
	("النجفي", "Al-Najafi"), ("الكربلائي", "Al-Karbalai"), ("الموصلي", "Al-Mosuli"), ("العنزي", "Al-Anazi"), ("الغريري", "Al-Ghreiri"),
]
KURDISH_FAMILIES = [("رسول", "Rasul"), ("عزيز", "Aziz"), ("قادر", "Qadir"), ("محمود", "Mahmood"), ("كريم", "Karim"), ("حمه", "Hama")]

# governorate -> (Arabic name, districts, share of the population of clients)
GOVERNORATES = {
	"Baghdad": ("بغداد", ["المنصور", "الكرادة", "زيونة", "الجادرية", "اليرموك", "حي الجامعة", "الأعظمية", "الكاظمية", "الدورة", "شارع فلسطين", "الحارثية", "الغدير"], 38),
	"Basra": ("البصرة", ["العشار", "الجزائر", "البراضعية", "الطويسة", "الزبير", "أبو الخصيب", "حي الحسين"], 13),
	"Erbil": ("أربيل", ["عنكاوا", "شارع المئة", "بختياري", "إسكان", "دريم سيتي"], 9),
	"Nineveh": ("نينوى", ["المجموعة الثقافية", "الزهور", "الحدباء", "النبي يونس"], 7),
	"Najaf": ("النجف", ["حي السعد", "حي الأنصار", "شارع الكوفة", "حي العدالة"], 6),
	"Karbala": ("كربلاء", ["حي الحسين", "باب بغداد", "حي الموظفين"], 5),
	"Sulaymaniyah": ("السليمانية", ["سالم ستريت", "رزكاري", "بكرجو", "شارع مولوي"], 5),
	"Kirkuk": ("كركوك", ["عرفة", "حي الواسطي", "القورية"], 4),
	"Babil": ("بابل", ["الحلة المركز", "حي الجمعية", "المحاويل"], 4),
	"Dhi Qar": ("ذي قار", ["الناصرية المركز", "حي الشموخ", "سوق الشيوخ"], 3),
	"Duhok": ("دهوك", ["مالطا", "شاخكي", "زاخو"], 2),
	"Diyala": ("ديالى", ["بعقوبة المركز", "الخالص"], 2),
	"Wasit": ("واسط", ["الكوت المركز", "الصويرة"], 1),
	"Maysan": ("ميسان", ["العمارة المركز"], 1),
	"Anbar": ("الأنبار", ["الرمادي المركز", "الفلوجة"], 1),
	"Qadisiyyah": ("القادسية", ["الديوانية المركز"], 1),
}

COMPANY_STEMS = [
	("دجلة", "Dijla"), ("الفرات", "Al-Furat"), ("بابل", "Babil"), ("سومر", "Sumer"), ("أكد", "Akkad"), ("آشور", "Ashur"),
	("النخيل", "Al-Nakheel"), ("الواحة", "Al-Waha"), ("الأمل", "Al-Amal"), ("النور", "Al-Noor"), ("الهلال", "Al-Hilal"),
	("الزوراء", "Al-Zawraa"), ("الكوثر", "Al-Kawthar"), ("البيان", "Al-Bayan"), ("أور", "Ur"), ("الوركاء", "Al-Warka"),
	("الجسر الذهبي", "Golden Bridge"), ("السنابل", "Al-Sanabel"), ("الياسمين", "Al-Yasmeen"), ("الأفق", "Al-Ufuq"),
	("المسار", "Al-Masar"), ("الراية", "Al-Raya"), ("الصفوة", "Al-Safwa"), ("الريادة", "Al-Riyada"), ("القمة", "Al-Qimma"),
	("شط العرب", "Shatt Al-Arab"), ("نينوى الحدباء", "Hadba"), ("زاكروس", "Zagros"), ("كوردستان الخضراء", "Green Kurdistan"),
]
COMPANY_ACTIVITIES = [
	("للمقاولات العامة", "General Contracting", "Construction"), ("للتجارة العامة", "General Trading", "Trading"),
	("للنقل والخدمات اللوجستية", "Transport & Logistics", "Logistics"), ("للصناعات الغذائية", "Food Industries", "Manufacturing"),
	("للأدوية والمستلزمات الطبية", "Pharmaceuticals", "Pharma"), ("للاستثمار السياحي", "Tourism Investment", "Hospitality"),
	("للخدمات النفطية", "Oilfield Services", "Energy"), ("للمواد الإنشائية", "Construction Materials", "Manufacturing"),
	("للسيارات والمعدات", "Automotive & Equipment", "Trading"), ("للطاقة والتوليد", "Power Generation", "Energy"),
	("للحديد والصلب", "Steel Industries", "Manufacturing"), ("للإلكترونيات", "Electronics", "Trading"),
	("للخدمات الأمنية", "Security Services", "Services"), ("للمولات والاستثمار العقاري", "Real Estate & Malls", "Real Estate"),
	("لتعبئة المياه والمشروبات", "Water & Beverages", "Manufacturing"), ("للدواجن والأعلاف", "Poultry & Feed", "Agriculture"),
]
COMPANY_FORMS = [("شركة", "Co."), ("مجموعة", "Group"), ("شركة", "Ltd.")]

PLATE_LETTERS = ["أ", "ب", "ج", "د", "هـ", "و", "ر", "س", "ط", "ك", "م", "ن"]

# ------------------------------------------------------------------- health (TPA)
SPECIALITIES = ["Internal Medicine", "General Surgery", "Pediatrics", "Obstetrics & Gynecology", "Orthopedics", "ENT", "Ophthalmology",
	"Dentistry", "Dermatology", "Cardiology", "Neurology", "Urology", "Endocrinology", "Psychiatry"]

# (code, English, Arabic, speciality, chronic)
ICD10 = [
	("J06.9", "Acute upper respiratory infection", "التهاب المجاري التنفسية العليا الحاد", "Internal Medicine", 0),
	("J02.9", "Acute pharyngitis", "التهاب البلعوم الحاد", "ENT", 0), ("J01.9", "Acute sinusitis", "التهاب الجيوب الأنفية الحاد", "ENT", 0),
	("J20.9", "Acute bronchitis", "التهاب القصبات الحاد", "Internal Medicine", 0), ("J18.9", "Pneumonia, unspecified", "ذات الرئة", "Internal Medicine", 0),
	("J45.9", "Asthma", "الربو القصبي", "Internal Medicine", 1), ("J30.4", "Allergic rhinitis", "التهاب الأنف التحسسي", "ENT", 0),
	("E11.9", "Type 2 diabetes mellitus", "داء السكري من النوع الثاني", "Endocrinology", 1), ("I10", "Essential hypertension", "ارتفاع ضغط الدم الأساسي", "Cardiology", 1),
	("E78.5", "Hyperlipidaemia", "ارتفاع دهون الدم", "Endocrinology", 1), ("E03.9", "Hypothyroidism", "قصور الغدة الدرقية", "Endocrinology", 1),
	("I25.1", "Ischaemic heart disease", "مرض القلب الإقفاري", "Cardiology", 1), ("I50.9", "Heart failure", "قصور القلب", "Cardiology", 1),
	("I21.9", "Acute myocardial infarction", "احتشاء عضلة القلب الحاد", "Cardiology", 0), ("I63.9", "Cerebral infarction", "الجلطة الدماغية", "Neurology", 0),
	("N18.9", "Chronic kidney disease", "القصور الكلوي المزمن", "Internal Medicine", 1), ("G40.9", "Epilepsy", "الصرع", "Neurology", 1),
	("G43.9", "Migraine", "الشقيقة", "Neurology", 0), ("R51", "Headache", "صداع", "Internal Medicine", 0),
	("K29.7", "Gastritis", "التهاب المعدة", "Internal Medicine", 0), ("K21.9", "Gastro-oesophageal reflux", "الارتجاع المريئي", "Internal Medicine", 0),
	("K35.8", "Acute appendicitis", "التهاب الزائدة الدودية الحاد", "General Surgery", 0), ("K80.2", "Gallstones without cholecystitis", "حصى المرارة", "General Surgery", 0),
	("K40.9", "Inguinal hernia", "الفتق الإربي", "General Surgery", 0), ("A09", "Gastroenteritis", "التهاب المعدة والأمعاء", "Pediatrics", 0),
	("N39.0", "Urinary tract infection", "التهاب المجاري البولية", "Urology", 0), ("N20.0", "Kidney stone", "حصى الكلية", "Urology", 0),
	("N40", "Benign prostatic hyperplasia", "تضخم البروستات الحميد", "Urology", 1), ("M54.5", "Low back pain", "ألم أسفل الظهر", "Orthopedics", 0),
	("M17.9", "Osteoarthritis of knee", "خشونة مفصل الركبة", "Orthopedics", 1), ("M51.2", "Lumbar disc displacement", "انزلاق غضروفي قطني", "Orthopedics", 0),
	("S82.2", "Fracture of shaft of tibia", "كسر عظم الساق", "Orthopedics", 0), ("S52.5", "Fracture of lower end of radius", "كسر نهاية عظم الكعبرة", "Orthopedics", 0),
	("O80", "Normal delivery", "ولادة طبيعية", "Obstetrics & Gynecology", 0), ("O82", "Caesarean delivery", "ولادة قيصرية", "Obstetrics & Gynecology", 0),
	("Z34.9", "Supervision of normal pregnancy", "متابعة حمل طبيعي", "Obstetrics & Gynecology", 0),
	("O20.0", "Threatened abortion", "إجهاض منذر", "Obstetrics & Gynecology", 0), ("H10.9", "Conjunctivitis", "التهاب الملتحمة", "Ophthalmology", 0),
	("H52.1", "Myopia", "قصر النظر", "Ophthalmology", 0), ("H25.9", "Senile cataract", "الساد (الماء الأبيض)", "Ophthalmology", 0),
	("H66.9", "Otitis media", "التهاب الأذن الوسطى", "ENT", 0), ("K02.9", "Dental caries", "تسوس الأسنان", "Dentistry", 0),
	("K05.1", "Chronic gingivitis", "التهاب اللثة المزمن", "Dentistry", 0), ("L20.9", "Atopic dermatitis", "التهاب الجلد التأتبي", "Dermatology", 0),
	("L70.0", "Acne vulgaris", "حب الشباب", "Dermatology", 0), ("F41.9", "Anxiety disorder", "اضطراب القلق", "Psychiatry", 0),
	("D50.9", "Iron deficiency anaemia", "فقر الدم بنقص الحديد", "Internal Medicine", 0), ("E66.9", "Obesity", "السمنة", "Endocrinology", 0),
	("C50.9", "Malignant neoplasm of breast", "سرطان الثدي", "General Surgery", 1), ("R10.4", "Abdominal pain", "ألم في البطن", "Internal Medicine", 0),
	("R50.9", "Fever", "حمى", "Pediatrics", 0), ("R07.4", "Chest pain", "ألم في الصدر", "Cardiology", 0), ("P59.9", "Neonatal jaundice", "يرقان الوليد", "Pediatrics", 0),
	("L03.9", "Cellulitis", "التهاب النسيج الخلوي", "Dermatology", 0), ("S06.0", "Concussion", "ارتجاج الدماغ", "Neurology", 0),
	("Z00.0", "General medical examination", "فحص طبي عام", "Internal Medicine", 0), ("B18.1", "Chronic viral hepatitis B", "التهاب الكبد الفيروسي ب المزمن", "Internal Medicine", 1),
]

# (code, English name, Arabic name, service category, benefit category, price IQD, requires pre-authorization, speciality)
SERVICES = [
	("CON-GP", "General practitioner consultation", "استشارة طبيب عام", "Consultation", "Outpatient", 15000, 0, "Internal Medicine"),
	("CON-SP", "Specialist consultation", "استشارة طبيب اختصاص", "Consultation", "Outpatient", 30000, 0, ""),
	("CON-CN", "Consultant consultation", "استشارة طبيب استشاري", "Consultation", "Outpatient", 40000, 0, ""),
	("CON-ER", "Emergency department visit", "مراجعة طوارئ", "Emergency", "Emergency", 35000, 0, ""),
	("CON-FU", "Follow-up visit", "مراجعة متابعة", "Consultation", "Outpatient", 15000, 0, ""),
	("LAB-CBC", "Complete blood count", "تحليل صورة الدم الكاملة", "Laboratory", "Laboratory and Radiology", 10000, 0, ""),
	("LAB-FBS", "Fasting blood sugar", "سكر الدم الصيامي", "Laboratory", "Laboratory and Radiology", 5000, 0, ""),
	("LAB-A1C", "HbA1c", "السكر التراكمي", "Laboratory", "Laboratory and Radiology", 15000, 0, ""),
	("LAB-LIP", "Lipid profile", "صورة الدهون", "Laboratory", "Laboratory and Radiology", 20000, 0, ""),
	("LAB-LFT", "Liver function tests", "وظائف الكبد", "Laboratory", "Laboratory and Radiology", 20000, 0, ""),
	("LAB-RFT", "Renal function tests", "وظائف الكلى", "Laboratory", "Laboratory and Radiology", 15000, 0, ""),
	("LAB-TSH", "Thyroid function (TSH)", "هرمون الغدة الدرقية", "Laboratory", "Laboratory and Radiology", 15000, 0, ""),
	("LAB-UA", "Urinalysis", "تحليل الإدرار العام", "Laboratory", "Laboratory and Radiology", 5000, 0, ""),
	("LAB-CUL", "Culture and sensitivity", "زرع وتحسس", "Laboratory", "Laboratory and Radiology", 20000, 0, ""),
	("LAB-VD", "Vitamin D level", "فيتامين د", "Laboratory", "Laboratory and Radiology", 25000, 0, ""),
	("LAB-CRP", "C-reactive protein", "بروتين سي التفاعلي", "Laboratory", "Laboratory and Radiology", 10000, 0, ""),
	("RAD-CXR", "Chest X-ray", "أشعة الصدر", "Radiology", "Laboratory and Radiology", 20000, 0, ""),
	("RAD-XL", "Limb X-ray", "أشعة الأطراف", "Radiology", "Laboratory and Radiology", 20000, 0, ""),
	("RAD-USA", "Abdominal ultrasound", "سونار البطن", "Radiology", "Laboratory and Radiology", 30000, 0, ""),
	("RAD-USP", "Obstetric ultrasound", "سونار الحمل", "Radiology", "Maternity", 30000, 0, "Obstetrics & Gynecology"),
	("RAD-ECHO", "Echocardiography", "إيكو القلب", "Radiology", "Laboratory and Radiology", 50000, 0, "Cardiology"),
	("RAD-ECG", "Electrocardiogram", "تخطيط القلب", "Radiology", "Laboratory and Radiology", 10000, 0, "Cardiology"),
	("RAD-CTB", "CT scan of brain", "مفراس الدماغ", "Radiology", "Laboratory and Radiology", 120000, 1, "Neurology"),
	("RAD-CTA", "CT scan of abdomen", "مفراس البطن", "Radiology", "Laboratory and Radiology", 175000, 1, ""),
	("RAD-MRS", "MRI of lumbar spine", "رنين الفقرات القطنية", "Radiology", "Laboratory and Radiology", 250000, 1, "Orthopedics"),
	("RAD-MRK", "MRI of knee", "رنين الركبة", "Radiology", "Laboratory and Radiology", 250000, 1, "Orthopedics"),
	("RAD-MAM", "Mammography", "تصوير الثدي الشعاعي", "Radiology", "Laboratory and Radiology", 60000, 0, ""),
	("PRC-END", "Upper GI endoscopy", "ناظور المعدة", "Surgery", "Outpatient", 250000, 1, "Internal Medicine"),
	("PRC-COL", "Colonoscopy", "ناظور القولون", "Surgery", "Outpatient", 350000, 1, "Internal Medicine"),
	("SUR-APP", "Appendicectomy", "عملية استئصال الزائدة الدودية", "Surgery", "Inpatient", 1500000, 1, "General Surgery"),
	("SUR-LCH", "Laparoscopic cholecystectomy", "استئصال المرارة بالناظور", "Surgery", "Inpatient", 2500000, 1, "General Surgery"),
	("SUR-HER", "Inguinal hernia repair", "عملية الفتق الإربي", "Surgery", "Inpatient", 1500000, 1, "General Surgery"),
	("SUR-TON", "Tonsillectomy", "استئصال اللوزتين", "Surgery", "Inpatient", 900000, 1, "ENT"),
	("SUR-CAT", "Cataract surgery with lens", "عملية الساد مع زرع عدسة", "Surgery", "Inpatient", 1200000, 1, "Ophthalmology"),
	("SUR-ARK", "Knee arthroscopy", "ناظور الركبة", "Surgery", "Inpatient", 2500000, 1, "Orthopedics"),
	("SUR-ORF", "Open reduction and internal fixation", "تثبيت كسر جراحي", "Surgery", "Inpatient", 3000000, 1, "Orthopedics"),
	("SUR-CAH", "Cardiac catheterisation", "قسطرة قلبية تشخيصية", "Surgery", "Inpatient", 3000000, 1, "Cardiology"),
	("SUR-PCI", "Coronary stent (PCI)", "قسطرة علاجية مع دعامة", "Surgery", "Inpatient", 7000000, 1, "Cardiology"),
	("MAT-NVD", "Normal vaginal delivery", "ولادة طبيعية", "Maternity", "Maternity", 1000000, 1, "Obstetrics & Gynecology"),
	("MAT-CS", "Caesarean section", "ولادة قيصرية", "Maternity", "Maternity", 2000000, 1, "Obstetrics & Gynecology"),
	("MAT-ANC", "Antenatal visit", "مراجعة حمل", "Maternity", "Maternity", 25000, 0, "Obstetrics & Gynecology"),
	("IP-WARD", "Ward bed per day", "رقود ردهة عامة (يومي)", "Inpatient Stay", "Inpatient", 150000, 1, ""),
	("IP-PRV", "Private room per day", "غرفة خاصة (يومي)", "Inpatient Stay", "Inpatient", 250000, 1, ""),
	("IP-ICU", "Intensive care per day", "عناية مركزة (يومي)", "Inpatient Stay", "Inpatient", 600000, 1, ""),
	("TRT-DIA", "Haemodialysis session", "جلسة غسيل كلى", "Other", "Chronic", 150000, 1, "Internal Medicine"),
	("TRT-CHE", "Chemotherapy session", "جلسة علاج كيميائي", "Other", "Chronic", 1500000, 1, ""),
	("PHY-SES", "Physiotherapy session", "جلسة علاج طبيعي", "Physiotherapy", "Physiotherapy", 25000, 0, "Orthopedics"),
	("DEN-FIL", "Dental filling", "حشوة سن", "Dental", "Dental", 40000, 0, "Dentistry"),
	("DEN-SCL", "Scaling and polishing", "تنظيف الأسنان", "Dental", "Dental", 35000, 0, "Dentistry"),
	("DEN-EXT", "Tooth extraction", "قلع سن", "Dental", "Dental", 30000, 0, "Dentistry"),
	("DEN-RCT", "Root canal treatment", "علاج عصب", "Dental", "Dental", 150000, 0, "Dentistry"),
	("DEN-CRN", "Dental crown", "تاج سني", "Dental", "Dental", 200000, 0, "Dentistry"),
	("OPT-EXM", "Eye examination", "فحص النظر", "Optical", "Optical", 20000, 0, "Ophthalmology"),
	("OPT-GLS", "Prescription glasses", "نظارة طبية", "Optical", "Optical", 75000, 0, "Ophthalmology"),
	("ER-NEB", "Nebuliser session", "جلسة بخار", "Emergency", "Emergency", 10000, 0, ""),
	("ER-IVF", "IV fluids", "مغذي وريدي", "Emergency", "Emergency", 15000, 0, ""),
	("ER-SUT", "Minor suturing", "خياطة جرح بسيط", "Emergency", "Emergency", 30000, 0, ""),
	("ER-CST", "Plaster cast application", "تجبير بالجبس", "Emergency", "Emergency", 75000, 0, "Orthopedics"),
	("COS-BTX", "Cosmetic botox injection", "حقن بوتوكس تجميلي", "Other", "Other", 300000, 0, "Dermatology"),
]

# (code, trade name, generic name, form and strength, price IQD, chronic, requires pre-authorization, covered, maximum quantity)
DRUGS = [
	("DR-0001", "Panadol", "Paracetamol", "Tablet 500 mg x24", 4000, 0, 0, 1, 4), ("DR-0002", "Augmentin", "Amoxicillin / Clavulanate", "Tablet 1 g x14", 18000, 0, 0, 1, 2),
	("DR-0003", "Zithromax", "Azithromycin", "Tablet 500 mg x3", 12000, 0, 0, 1, 2), ("DR-0004", "Ciprobay", "Ciprofloxacin", "Tablet 500 mg x10", 9000, 0, 0, 1, 2),
	("DR-0005", "Suprax", "Cefixime", "Capsule 400 mg x5", 14000, 0, 0, 1, 2), ("DR-0006", "Brufen", "Ibuprofen", "Tablet 400 mg x30", 3500, 0, 0, 1, 3),
	("DR-0007", "Voltaren", "Diclofenac sodium", "Tablet 50 mg x20", 4500, 0, 0, 1, 3), ("DR-0008", "Losec", "Omeprazole", "Capsule 20 mg x14", 8000, 0, 0, 1, 4),
	("DR-0009", "Nexium", "Esomeprazole", "Tablet 40 mg x14", 15000, 0, 0, 1, 4), ("DR-0010", "Glucophage", "Metformin", "Tablet 850 mg x30", 6000, 1, 0, 1, 6),
	("DR-0011", "Diamicron MR", "Gliclazide", "Tablet 60 mg x30", 9000, 1, 0, 1, 6), ("DR-0012", "Lantus SoloStar", "Insulin glargine", "Pen 100 IU/ml x5", 45000, 1, 1, 1, 3),
	("DR-0013", "Januvia", "Sitagliptin", "Tablet 100 mg x28", 35000, 1, 0, 1, 3), ("DR-0014", "Norvasc", "Amlodipine", "Tablet 5 mg x30", 7000, 1, 0, 1, 6),
	("DR-0015", "Zestril", "Lisinopril", "Tablet 10 mg x28", 6000, 1, 0, 1, 6), ("DR-0016", "Diovan", "Valsartan", "Tablet 160 mg x28", 14000, 1, 0, 1, 6),
	("DR-0017", "Concor", "Bisoprolol", "Tablet 5 mg x30", 8000, 1, 0, 1, 6), ("DR-0018", "Lipitor", "Atorvastatin", "Tablet 20 mg x30", 16000, 1, 0, 1, 6),
	("DR-0019", "Crestor", "Rosuvastatin", "Tablet 10 mg x28", 18000, 1, 0, 1, 6), ("DR-0020", "Aspirin Protect", "Acetylsalicylic acid", "Tablet 100 mg x30", 3000, 1, 0, 1, 6),
	("DR-0021", "Plavix", "Clopidogrel", "Tablet 75 mg x28", 25000, 1, 0, 1, 6), ("DR-0022", "Euthyrox", "Levothyroxine", "Tablet 50 mcg x50", 5000, 1, 0, 1, 6),
	("DR-0023", "Ventolin", "Salbutamol", "Inhaler 100 mcg", 6000, 0, 0, 1, 2), ("DR-0024", "Symbicort", "Budesonide / Formoterol", "Inhaler 160/4.5", 40000, 1, 0, 1, 3),
	("DR-0025", "Singulair", "Montelukast", "Tablet 10 mg x28", 18000, 1, 0, 1, 3), ("DR-0026", "Zyrtec", "Cetirizine", "Tablet 10 mg x20", 4000, 0, 0, 1, 3),
	("DR-0027", "Claritin", "Loratadine", "Tablet 10 mg x20", 4500, 0, 0, 1, 3), ("DR-0028", "Predsol", "Prednisolone", "Tablet 5 mg x30", 3000, 0, 0, 1, 2),
	("DR-0029", "Fucidin", "Fusidic acid", "Cream 2% 15 g", 6000, 0, 0, 1, 2), ("DR-0030", "Flagyl", "Metronidazole", "Tablet 500 mg x20", 3000, 0, 0, 1, 2),
	("DR-0031", "Diflucan", "Fluconazole", "Capsule 150 mg x1", 8000, 0, 0, 1, 2), ("DR-0032", "Vi-De 3", "Cholecalciferol", "Capsule 50,000 IU x4", 8000, 0, 0, 1, 2),
	("DR-0033", "Ferro-Folgamma", "Ferrous sulphate / folic acid", "Capsule x20", 4000, 0, 0, 1, 3), ("DR-0034", "Motilium", "Domperidone", "Tablet 10 mg x30", 5000, 0, 0, 1, 2),
	("DR-0035", "Buscopan", "Hyoscine butylbromide", "Tablet 10 mg x20", 4500, 0, 0, 1, 2), ("DR-0036", "Calpol", "Paracetamol", "Syrup 120 mg/5 ml", 3500, 0, 0, 1, 3),
	("DR-0037", "Amoxil", "Amoxicillin", "Suspension 250 mg/5 ml", 5000, 0, 0, 1, 2), ("DR-0038", "Clexane", "Enoxaparin", "Injection 40 mg x2", 12000, 0, 1, 1, 10),
	("DR-0039", "Humira", "Adalimumab", "Pre-filled pen 40 mg", 900000, 1, 1, 1, 2), ("DR-0040", "Eprex", "Epoetin alfa", "Injection 4000 IU x6", 60000, 1, 1, 1, 4),
	("DR-0041", "Herceptin", "Trastuzumab", "Vial 440 mg", 2500000, 1, 1, 1, 1), ("DR-0042", "Roaccutane", "Isotretinoin", "Capsule 20 mg x30", 35000, 0, 0, 0, 1),
	("DR-0043", "Viagra", "Sildenafil", "Tablet 50 mg x4", 20000, 0, 0, 0, 1), ("DR-0044", "Xenical", "Orlistat", "Capsule 120 mg x42", 45000, 0, 0, 0, 1),
	("DR-0045", "Centrum", "Multivitamins", "Tablet x30", 15000, 0, 0, 0, 1), ("DR-0046", "Tegretol", "Carbamazepine", "Tablet 200 mg x50", 9000, 1, 0, 1, 4),
	("DR-0047", "Depakine Chrono", "Sodium valproate", "Tablet 500 mg x30", 14000, 1, 0, 1, 4), ("DR-0048", "Xatral", "Alfuzosin", "Tablet 10 mg x30", 16000, 1, 0, 1, 3),
	("DR-0049", "Cipralex", "Escitalopram", "Tablet 10 mg x28", 15000, 1, 0, 1, 3), ("DR-0050", "Lasix", "Furosemide", "Tablet 40 mg x20", 3000, 1, 0, 1, 4),
	("DR-0051", "Viread", "Tenofovir", "Tablet 300 mg x30", 70000, 1, 1, 1, 2), ("DR-0052", "Gaviscon", "Alginate / antacid", "Suspension 200 ml", 6000, 0, 0, 1, 2),
	("DR-0053", "Strepsils", "Amylmetacresol lozenges", "Lozenges x24", 4000, 0, 0, 1, 2), ("DR-0054", "Otrivin", "Xylometazoline", "Nasal spray 0.1%", 4000, 0, 0, 1, 2),
	("DR-0055", "Tobradex", "Tobramycin / dexamethasone", "Eye drops 5 ml", 9000, 0, 0, 1, 2), ("DR-0056", "Daktarin", "Miconazole", "Oral gel 40 g", 6500, 0, 0, 1, 2),
]
NOT_COVERED_KEYWORD = "Cosmetic"

# fictional health providers: (Arabic, English, type, speciality list, governorate, accreditation)
PROVIDERS = [
	("مستشفى الحياة الأهلي", "Al-Hayat Private Hospital", "Hospital", ["General Surgery", "Internal Medicine", "Obstetrics & Gynecology", "Pediatrics"], "Baghdad", "A"),
	("مستشفى دار الشفاء التخصصي", "Dar Al-Shifaa Specialist Hospital", "Hospital", ["Cardiology", "General Surgery", "Orthopedics"], "Baghdad", "A"),
	("مستشفى النخبة الجراحي", "Al-Nukhba Surgical Hospital", "Hospital", ["General Surgery", "Urology", "ENT"], "Baghdad", "A"),
	("مستشفى الرحمة الأهلي", "Al-Rahma Private Hospital", "Hospital", ["Internal Medicine", "Obstetrics & Gynecology"], "Baghdad", "B"),
	("مستشفى الياسمين للولادة", "Al-Yasmeen Maternity Hospital", "Hospital", ["Obstetrics & Gynecology", "Pediatrics"], "Baghdad", "B"),
	("مستشفى شط العرب الأهلي", "Shatt Al-Arab Private Hospital", "Hospital", ["General Surgery", "Internal Medicine", "Cardiology"], "Basra", "A"),
	("مستشفى الموانئ التخصصي", "Ports Specialist Hospital", "Hospital", ["Orthopedics", "General Surgery"], "Basra", "B"),
	("مستشفى زاكروس الدولي", "Zagros International Hospital", "Hospital", ["Cardiology", "Neurology", "General Surgery"], "Erbil", "A"),
	("مستشفى السلام الأهلي - النجف", "Al-Salam Private Hospital Najaf", "Hospital", ["Internal Medicine", "General Surgery"], "Najaf", "B"),
	("مستشفى الحدباء الأهلي", "Al-Hadba Private Hospital", "Hospital", ["Internal Medicine", "Orthopedics"], "Nineveh", "B"),
	("مستشفى الوركاء الأهلي - كربلاء", "Al-Warka Private Hospital Karbala", "Hospital", ["Obstetrics & Gynecology", "General Surgery"], "Karbala", "B"),
	("مستشفى آزادي الأهلي", "Azadi Private Hospital", "Hospital", ["Internal Medicine", "Pediatrics"], "Sulaymaniyah", "B"),
	("مركز النور الطبي التخصصي", "Al-Noor Specialist Medical Center", "Clinic / Medical Center", ["Internal Medicine", "Endocrinology", "Cardiology"], "Baghdad", "A"),
	("مجمع الكرادة الطبي", "Karrada Medical Complex", "Clinic / Medical Center", ["Internal Medicine", "Dermatology", "ENT"], "Baghdad", "B"),
	("مركز المنصور لطب الأطفال", "Al-Mansour Pediatric Center", "Clinic / Medical Center", ["Pediatrics"], "Baghdad", "B"),
	("عيادات الجادرية الاستشارية", "Jadriya Consultant Clinics", "Clinic / Medical Center", ["Neurology", "Psychiatry", "Endocrinology"], "Baghdad", "A"),
	("مركز العشار الطبي", "Ashar Medical Center", "Clinic / Medical Center", ["Internal Medicine", "Pediatrics"], "Basra", "B"),
	("مركز عنكاوا الطبي", "Ankawa Medical Center", "Clinic / Medical Center", ["Internal Medicine", "Dermatology"], "Erbil", "B"),
	("مركز الكوفة الطبي", "Kufa Medical Center", "Clinic / Medical Center", ["Internal Medicine"], "Najaf", "C"),
	("مركز الحلة الطبي", "Hilla Medical Center", "Clinic / Medical Center", ["Internal Medicine", "Pediatrics"], "Babil", "C"),
	("عيادة الدكتور ليث الحسيني للقلبية", "Dr. Laith Al-Husseini Cardiology Clinic", "Doctor", ["Cardiology"], "Baghdad", "A"),
	("عيادة الدكتورة زينب الربيعي النسائية", "Dr. Zainab Al-Rubaie Women's Clinic", "Doctor", ["Obstetrics & Gynecology"], "Baghdad", "B"),
	("عيادة الدكتور كرار الخفاجي للعظام", "Dr. Karrar Al-Khafaji Orthopedic Clinic", "Doctor", ["Orthopedics"], "Basra", "B"),
	("مختبرات الحياة التخصصية", "Al-Hayat Specialist Laboratories", "Laboratory", [], "Baghdad", "A"),
	("مختبر الدقة للتحليلات المرضية", "Al-Diqqa Pathology Laboratory", "Laboratory", [], "Baghdad", "B"),
	("مختبرات البيان", "Al-Bayan Laboratories", "Laboratory", [], "Basra", "B"),
	("مختبر سومر", "Sumer Laboratory", "Laboratory", [], "Erbil", "B"),
	("مختبر الأمل", "Al-Amal Laboratory", "Laboratory", [], "Najaf", "C"),
	("مركز الرافد للأشعة والسونار", "Al-Rafid Radiology Center", "Radiology Center", [], "Baghdad", "A"),
	("مركز الفرات للتصوير الطبي", "Al-Furat Medical Imaging", "Radiology Center", [], "Babil", "B"),
	("مركز الخليج للأشعة", "Gulf Radiology Center", "Radiology Center", [], "Basra", "B"),
	("صيدلية الشفاء", "Al-Shifaa Pharmacy", "Pharmacy", [], "Baghdad", "B"), ("صيدلية النهرين", "Nahrain Pharmacy", "Pharmacy", [], "Baghdad", "B"),
	("صيدلية الحكمة", "Al-Hikma Pharmacy", "Pharmacy", [], "Baghdad", "B"), ("صيدلية زيونة المركزية", "Zayouna Central Pharmacy", "Pharmacy", [], "Baghdad", "B"),
	("صيدلية الجمعية", "Al-Jamia Pharmacy", "Pharmacy", [], "Basra", "B"), ("صيدلية المئة", "Street 100 Pharmacy", "Pharmacy", [], "Erbil", "B"),
	("صيدلية الكوثر", "Al-Kawthar Pharmacy", "Pharmacy", [], "Najaf", "C"), ("صيدلية الحسين", "Al-Hussein Pharmacy", "Pharmacy", [], "Karbala", "C"),
	("مركز البسمة لطب الأسنان", "Al-Basma Dental Center", "Dental Center", ["Dentistry"], "Baghdad", "A"),
	("مركز اللؤلؤة لطب الأسنان", "Pearl Dental Center", "Dental Center", ["Dentistry"], "Erbil", "B"),
	("مركز الحركة للعلاج الطبيعي", "Al-Haraka Physiotherapy Center", "Physiotherapy Center", ["Orthopedics"], "Baghdad", "B"),
	("مركز البصر لطب العيون", "Al-Basar Eye Center", "Other Specialty", ["Ophthalmology"], "Baghdad", "A"),
]

# TPA clients: (Arabic, English, type, fee basis, fee rate, governorate)
TPA_CLIENTS = [
	("شركة سنابل الخير للتأمين", "Sanabel Al-Khair Insurance Co.", "Insurance Company", "Percent of Claims", 6, "Baghdad"),
	("شركة جسر الرافدين للتأمين", "Rafidain Bridge Insurance Co.", "Insurance Company", "Percent of Claims", 5.5, "Baghdad"),
	("مصرف الواحة التجاري", "Al-Waha Commercial Bank", "Corporate Client", "Per Member Per Month", 4500, "Baghdad"),
	("شركة أور للاتصالات المتنقلة", "Ur Mobile Telecom Co.", "Corporate Client", "Per Member Per Month", 5000, "Baghdad"),
	("كلية سومر الجامعة الأهلية", "Sumer Private University College", "Corporate Client", "Percent of Claims", 7, "Babil"),
	("شركة نفط الأفق للخدمات", "Al-Ufuq Petroleum Services", "Self-Funded Scheme", "Per Member Per Month", 6000, "Basra"),
]
EMPLOYERS = {c[1]: c[0] for c in TPA_CLIENTS}

SUBJECTS_COMPLAINT = ["تأخر الموافقة على عملية جراحية", "رفض مطالبة صيدلية دون توضيح", "طلب مستشفى مبلغاً إضافياً من المريض",
	"عدم قبول البطاقة في صيدلية متعاقدة", "تأخر صرف مستحقات المستشفى", "سوء معاملة في قسم الاستقبال", "خطأ في اسم المستفيد على البطاقة"]
SUBJECTS_INQUIRY = ["الاستفسار عن الرصيد المتبقي للمنافع", "قائمة المستشفيات المتعاقدة في البصرة", "هل تغطي الخطة علاج الأسنان؟",
	"كيفية إضافة مولود جديد إلى الوثيقة", "طلب بطاقة بدل ضائع", "الاستفسار عن حالة مطالبة استرداد", "هل يشمل التأمين الولادة القيصرية؟",
	"كيف أحصل على موافقة مسبقة للرنين؟", "مواعيد عمل مركز خدمة الأعضاء"]
SUBJECTS_SUGGESTION = ["إضافة صيدليات في قضاء الزبير", "تطبيق للهاتف لعرض البطاقة", "تمديد ساعات خط الطوارئ"]
