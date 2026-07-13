"""Add aliases / cautions / details metadata to every asana in data/asanas.json.

Sources: zhihu p/441113137 (28 体式解剖图 补充要点 = details), zhihu p/28217320
(13 正误对比 = cautions), helloyogis alignment notes, and domain knowledge.
Fields are inserted right after `benefits` to keep a readable field order.
Idempotent: re-running overwrites the three fields with the curated values.
"""
from __future__ import annotations
import json

CUR = "data/asanas.json"

# id -> {aliases, cautions, details}
META = {
    "downward_dog": {
        "aliases": ["Adho Mukha Svanasana", "下犬式", "下狗式", "顶峰式"],
        "cautions": ["不要弓背，脊柱保持延展", "初学者可微屈膝，先把臀部向上向后推高", "不要耸肩，肩膀远离耳朵"],
        "details": ["大小腿前侧收紧上提、后侧延展", "骨盆向前转动，脊柱充分延展", "肩部放松下沉，斜方肌向后向上", "大臂外旋、小臂内旋，双手压实垫面"],
    },
    "tree": {
        "aliases": ["Vrksasana", "树式"],
        "cautions": ["脚掌踩大腿内侧或小腿内侧，避免直接压膝关节", "骨盆保持中正，不要向支撑侧外翻", "核心收紧、目视前方一点以稳定平衡"],
        "details": ["屈膝腿外旋，脚掌与大腿内侧互推", "支撑脚用力向下踩，大腿收紧向上提", "双手合十或上举，肩膀下沉"],
    },
    "triangle": {
        "aliases": ["Utthita Trikonasana", "三角伸展式", "三角式"],
        "cautions": ["不要为了手触地而弓背或侧塌腰", "躯干保持在两腿同一平面内侧倾，不要前趴", "前腿膝盖不要超伸锁死"],
        "details": ["双腿大腿肌肉收紧向上提", "髋部与胸腔向上向外打开", "上方手臂向上延展有力，双臂成一条直线"],
    },
    "warrior1": {
        "aliases": ["Virabhadrasana I", "战士第一式", "勇士一式"],
        "cautions": ["前膝不超过脚踝，膝盖与脚尖同向", "后脚外缘踩实，脚跟不掀起", "髋部摆正朝向正前方，避免歪斜"],
        "details": ["屈膝腿收紧，膝盖对准脚尖方向", "腹部收紧上提，背部向上延展", "后侧伸直腿髋部尽量向前推"],
    },
    "warrior2": {
        "aliases": ["Virabhadrasana II", "战士第二式", "勇士二式"],
        "cautions": ["前膝对准中间脚趾，不要内扣", "躯干保持竖直，不要向前腿倾倒", "肩膀下沉，不要耸肩"],
        "details": ["后方腿外旋，大腿收紧上提", "胸腔打开上提，腹部微微收紧", "大臂外旋、小臂内旋，双臂向两侧延展"],
    },
    "warrior3": {
        "aliases": ["Virabhadrasana III", "战士第三式", "勇士三式"],
        "cautions": ["保持两侧髋部等高，不要外翻", "躯干与后腿成一直线平行地面", "支撑腿膝盖微屈不锁死，核心收紧稳定"],
        "details": ["手臂与双腿向相反方向延展", "支撑腿脚用力向下踩，大腿收紧", "臀部收紧、背部延展，大臂外旋"],
    },
    "chair": {
        "aliases": ["Utkatasana", "幻椅式", "椅子式", "顶天式"],
        "cautions": ["重心落在脚跟，膝盖不超过脚尖", "不要塌腰翘臀，尾骨微微内收", "手臂上举时肩膀下沉不耸肩"],
        "details": ["屈髋屈膝像坐椅子，大腿趋向平行地面", "脊柱延展、手臂上举贴近耳侧", "核心收紧，胸腔上提"],
    },
    "plank": {
        "aliases": ["Phalakasana", "Kumbhakasana", "平板支撑", "斜板式"],
        "cautions": ["臀部不要抬太高，也不要塌腰下沉", "肩膀在手腕正上方", "核心收紧，颈部延展不低头"],
        "details": ["腹部内收，胸腔向前延展", "双手压地、肩膀下沉，从头到脚跟成一直线", "大腿前侧收紧、脚跟向后蹬"],
    },
    "bridge": {
        "aliases": ["Setu Bandha Sarvangasana", "桥式", "小桥式"],
        "cautions": ["膝盖不外翻，与脚尖同向", "下巴微收保护颈椎，不用颈部承重", "双脚踩实、平行髋宽"],
        "details": ["腹股沟与髋部打开，胸腔打开上提", "臀部收紧，大腿前侧收紧上提", "双腿向中线靠拢，双臂压地辅助"],
    },
    "cobra": {
        "aliases": ["Bhujangasana", "眼镜蛇式"],
        "cautions": ["不要耸肩，肩膀下沉远离耳朵", "耻骨贴地，用背部力量而非手臂硬撑", "颈部自然延展，不要过度后仰"],
        "details": ["腹部微微收紧，胸腔打开上提", "双手轻推地，肘部贴近身体", "大腿与脚背压实垫面"],
    },
    "camel": {
        "aliases": ["Ustrasana", "骆驼式"],
        "cautions": ["髋部不要后移，保持在膝盖正上方", "先上提胸腔再后弯，不要直接塌腰折颈", "颈部放松延展，量力后仰"],
        "details": ["大腿后侧与臀部收紧上提", "小腿脚背压实垫面，胸腔打开", "腹部与大腿前侧充分延展"],
    },
    "boat": {
        "aliases": ["Navasana", "Paripurna Navasana", "船式", "全船式"],
        "cautions": ["不要弓背，保持背部立直", "初学可双手抓小腿或屈膝辅助", "肩膀放松下沉，不要憋气"],
        "details": ["核心收紧、脊柱延展", "大腿收紧向上提，双腿伸直", "双肩放松下沉、颈部延展"],
    },
    "handstand": {
        "aliases": ["Adho Mukha Vrksasana", "手倒立", "倒立式"],
        "cautions": ["初学靠墙练习，循序渐进", "肩膀在手腕正上方，充分推地", "肋骨内收避免塌腰，颈部放松"],
        "details": ["双手压地、肩膀上提远离地面", "核心收紧，身体成一条竖直线", "双腿并拢向上延展、脚尖回勾上指"],
    },
    "crow": {
        "aliases": ["Bakasana", "Kakasana", "鹤禅式", "乌鸦式"],
        "cautions": ["目视前方防止前翻，前方垫软物", "核心收紧，膝盖夹紧上臂", "手腕负荷大，练前充分热身"],
        "details": ["双膝抵住上臂后侧，重心前移", "核心收紧、脚尖点地慢慢离地", "双手五指张开压地稳定"],
    },
    "paschimottanasana": {
        "aliases": ["Paschimottanasana", "坐立前屈", "西方伸展式", "背部前屈伸展式"],
        "cautions": ["从髋部折叠，不要弓背含胸", "可微屈膝或用瑜伽带勾脚", "腘绳肌紧的人不要强拉硬压"],
        "details": ["骨盆向前转动，肩部打开变宽", "斜方肌向后向下沉，大腿后侧延展", "腹部内收，胸腔找大腿"],
    },
    "upavistha_konasana": {
        "aliases": ["Upavistha Konasana", "坐角式", "坐广角式"],
        "cautions": ["脚尖朝上不向内倒，膝盖朝上", "不要弓背，从髋部向前折叠", "量力而行，避免拉伤内收肌"],
        "details": ["双腿外旋，坐骨压实垫面", "脊柱向上延展，胸腔打开", "双手向前带动躯干折叠"],
    },
    "salabhasana": {
        "aliases": ["Salabhasana", "蝗虫式"],
        "cautions": ["不要耸肩，双肩变宽下沉", "用背部与臀部力量抬起，颈部不后仰过度", "腹部收紧保护腰椎"],
        "details": ["胸部打开上提，双肩变宽下沉", "斜方肌向后向下，臀部微微收紧", "腹部收紧，腰背部肌肉加强"],
    },
    "dhanurasana": {
        "aliases": ["Dhanurasana", "弓式"],
        "cautions": ["双膝不外张，与髋同宽", "用小腿蹬手带动胸腔上提，均匀呼吸", "腰椎不适者慎做"],
        "details": ["双腿与双手对抗拉力，把身体展开成弓形", "核心收紧、背部有力，胸腔打开", "双腿向中线夹，下巴微微内收"],
    },
    "makarasana": {
        "aliases": ["Makarasana", "鳄鱼式", "放松式"],
        "cautions": ["属俯卧放松体式，全身放松不发力", "肩颈放松，额头或叠放的手背垫下巴", "呼吸深长自然"],
        "details": ["俯卧、双腿舒适分开，脚尖外展", "双臂交叠垫于额下或下巴", "腹式呼吸，随呼气进一步放松"],
    },
    "natarajasana": {
        "aliases": ["Natarajasana", "舞王式", "舞蹈式"],
        "cautions": ["支撑腿膝盖微屈不锁死，脚掌踩实", "先延展脊柱再后弯，髋部保持朝前", "核心收紧防止晃动"],
        "details": ["支撑腿大腿收紧上提", "后腿向上向后蹬、抓脚手带动胸腔打开", "对侧手臂向前延展平衡"],
    },
    "garudasana": {
        "aliases": ["Garudasana", "鹰式"],
        "cautions": ["屈膝微蹲降低重心以稳定", "肩膀下沉不耸肩", "核心收紧、目视前方一点"],
        "details": ["缠绕腿尽量内旋内收", "支撑腿大腿收紧向上提", "双手臂内收缠绕、手掌互推有力"],
    },
    "urdhva_dhanurasana": {
        "aliases": ["Urdhva Dhanurasana", "Chakrasana", "轮式", "上弓式", "全轮式"],
        "cautions": ["手肘不外张、双脚不外翻", "肩关节充分打开再上推，避免颈腰代偿", "起落用手脚均匀发力，量力而行"],
        "details": ["双手双脚用力向下压垫面", "背部肌肉收紧、核心微微内收", "腹股沟与髋部打开，胸腔向前向上推"],
    },
    "pincha_mayurasana": {
        "aliases": ["Pincha Mayurasana", "前臂倒立", "孔雀起舞式"],
        "cautions": ["初学靠墙练习", "前臂平行压实，肩膀上提防塌肩", "肋骨内收避免塌腰"],
        "details": ["前臂压地、肩膀上提远离地面", "核心收紧，身体成一直线", "双腿并拢向上延展、脚尖上指"],
    },
    "extended_hand_to_toe": {
        "aliases": ["Utthita Hasta Padangusthasana", "站立手抓大脚趾式", "单腿站立伸展式"],
        "cautions": ["支撑腿膝盖不锁死", "腘绳肌紧可屈膝或用瑜伽带勾脚", "核心收紧、骨盆端正防止晃动"],
        "details": ["支撑腿大腿收紧稳定", "抬起腿伸直、手抓大脚趾", "脊柱延展、两侧髋部等高"],
    },
    "gate": {
        "aliases": ["Parighasana", "门闩式"],
        "cautions": ["侧弯保持在同一平面，不要前倾含胸", "伸直腿膝盖朝上、脚掌踩实", "坐骨不后翘，髋部稳定"],
        "details": ["跪姿一腿向侧伸直，脚掌踩地", "躯干向伸直腿方向侧弯", "上方手臂过头延展、侧腰拉长"],
    },
    "low_lunge": {
        "aliases": ["Anjaneyasana", "新月式", "低位弓步", "骑马式"],
        "cautions": ["前膝不超过脚踝、前脚跟不抬起", "髋部向前向下沉并摆正", "后侧膝与脚背贴地舒适承重"],
        "details": ["腹部内收上提，前脚跟用力", "后腿脚背贴地、髋部向前向下", "手臂上举时胸腔打开、肩膀下沉"],
    },
    "side_angle": {
        "aliases": ["Utthita Parsvakonasana", "侧角伸展式", "侧角式"],
        "cautions": ["前膝对准中趾不内扣", "躯干与腿保持同一平面，不要前趴", "从后脚外缘到上方指尖成一条斜线"],
        "details": ["伸直腿外旋，大腿收紧向上提", "屈膝腿收紧、尽量靠近支撑手臂", "上方侧腰延展，手臂向斜上方伸展"],
    },
}

ORDER = ["id", "name_en", "name_sanskrit", "name_zh", "category", "difficulty",
         "benefits", "aliases", "cautions", "details", "ref_url", "muscles", "rules"]

db = json.load(open(CUR))
missing = []
for a in db["asanas"]:
    m = META.get(a["id"])
    if not m:
        missing.append(a["id"]); continue
    a["aliases"] = m["aliases"]
    a["cautions"] = m["cautions"]
    a["details"] = m["details"]
    # reorder keys for readability
    reordered = {k: a[k] for k in ORDER if k in a}
    for k in a:  # keep any stray keys
        if k not in reordered:
            reordered[k] = a[k]
    a.clear(); a.update(reordered)

with open(CUR, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Patched {len(db['asanas']) - len(missing)}/{len(db['asanas'])} asanas")
if missing:
    print("MISSING metadata for:", missing)
