"""Writes the Spiritual Gifts Today lesson family (all-views + one version per approved tradition) into lessons/source/.
The shared sections are written once so every version teaches the common ground identically."""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "source")

HEAD = """code: {code}
family: spiritual-gifts
version: {version}
issue: spiritual-gifts
title: Gifts of the Spirit
big_idea: {big_idea}
topic: Gifts from God
also: Holy Spirit; Tongues (the Gift); Charism; Church
audience: adults
minutes: 45
translation: KJV
passage: 1 Corinthians 12:1-11
"""

SHARED = """== opening | 4
Ask: "If you could ask God for one spiritual gift, what would it be, and why?" Let people answer. Then ask: "How do you know what gifts God has given you?" Today we look at Paul's teaching on spiritual gifts. All Christians share most of it, though they differ about some of the gifts today.

== scripture | 3
Read the passage aloud. Ask the class to listen for how many times Paul says "the same Spirit."

== background | 5
The church at Corinth was richly gifted (1:7) but proud and divided. Some prized spectacular gifts, especially speaking in tongues, as signs of spiritual superiority. Chapters 12-14 correct this. Chapter 12 teaches that all the gifts come from one Spirit for the good of the whole body; chapter 13 says that love matters more than any gift; chapter 14 gives practical rules for orderly worship.

Paul uses several words for the gifts: "spiritual gifts" (v. 1), "gifts" (Greek charismata, gifts of grace, v. 4), "administrations" or ministries (v. 5), and "operations" or workings (v. 6). The list in verses 8-10 includes wisdom, knowledge, faith, healing, miracles, prophecy, discerning of spirits, tongues and interpretation.

== point | {m1} | The Spirit leads us to confess Jesus as Lord
Paul begins with a test: "no man can say that Jesus is the Lord, but by the Holy Ghost" (v. 3). The Spirit's first and greatest work is to bring people to honour Jesus. Any claimed spiritual experience that does not exalt Christ is not from the Holy Spirit.
verses: 1 Corinthians 12:1-3; John 16:13-14; 1 John 4:1-3
quote: 51152 | The design of the passage is to give them some simple general guide by which they could at once recognize the operations of the Spirit of God
blank: No man can say that Jesus is the Lord, but by the Holy ____. | Ghost (Spirit)
blank: The Spirit's first work is to ____ Jesus. | honour (glorify)

== point | {m2} | One Spirit, many gifts, for the common good
"There are diversities of gifts, but the same Spirit" (v. 4). Every believer is given some "manifestation of the Spirit ... to profit withal," that is, for the common good (v. 7). Gifts are not trophies to display but tools to serve others. No one has every gift, and no one has none.
verses: 1 Corinthians 12:4-7; Romans 12:4-8; 1 Peter 4:10-11
quote: 43781 | Whatever gifts God has bestowed, or in what various ways soever the Spirit of God may have manifested himself, it is all for the common benefit of the Church.
quote: 24652 | Gifts and graces, charismata and charis, greatly differ.
blank: There are diversities of gifts, but the same ____. | Spirit
blank: Gifts are given for the common ____. | good
"""

POINT3_SHARED = """== point | 4 | The Spirit gives as he wills, and love is the more excellent way
"All these worketh that one and the selfsame Spirit, dividing to every man severally as he will" (v. 11). The Spirit decides who receives which gift, so there is no room for pride or envy. Paul goes on to show "a more excellent way" (12:31): love, without which every gift is empty (13:1-3).
verses: 1 Corinthians 12:11; 1 Corinthians 12:31; 1 Corinthians 13:1-3
quote: 51160 | All these are to be traced to him.
quote: 43796 | A man may possess the best of all these gifts, and yet be deficient in what is essentially necessary to his salvation, for he may be without that love
blank: The Spirit divides to every man severally as he ____. | will
blank: Without ____, every gift is empty. | love
"""

DIFFER = """== differ | {md} | Where Christians differ
Christians agree that the Holy Spirit gives gifts to every believer for the good of the church; that the Spirit leads us to confess Jesus as Lord; that gifts must be used in love and in good order (1 Corinthians 14:40); that God hears and answers prayer for the sick; and that every claim to speak for God must be tested by Scripture. They differ over whether the more extraordinary gifts listed in verses 8-10 (prophecy, tongues, interpretation, gifts of healing and miracles) continue in the church today in the same way as in the apostles' time, and over whether there is a "baptism in the Holy Spirit" after conversion, marked by speaking in tongues. Here are the main views of the five traditions, each described as its own teachers would describe it. Within most traditions, individual churches and believers vary.
view: baptist
view: wesleyan
view: reformed
view: lutheran
view: pentecostal
note: This topic can stir strong feelings, especially for anyone who has been hurt by excesses or by dismissive attitudes. Keep the discussion focused on Scripture and on love (1 Corinthians 13), and describe each view as its own members would.
"""

CLOSE = """== questions | {mq}
{questions}

== application | 2
{application}

== prayer | 2
{prayer}
"""

Q1 = "q: What do all Christians agree about spiritual gifts, according to this passage? | They come from the one Spirit; every believer has some; they are for the common good; the Spirit leads us to confess Jesus as Lord; they must be used in love."
Q_SERVE = "q: What gifts has God given you, and how could you use one this week to serve others? | Answers will vary: teaching, encouragement, hospitality, giving, helping, leadership, prayer, mercy."
Q_GRACE = "q: How can we hold our own convictions about the gifts while loving believers who see this differently? | By grounding our view in Scripture, describing others fairly, refusing pride or suspicion, and remembering that love is the more excellent way."

TRADITIONS = {
    "baptist": dict(
        big_idea="The one Spirit gives every believer gifts for the common good; many Baptists hold that the miraculous sign gifts marked the apostles' age, while the Spirit's gifts for service continue in every church.",
        heading="The Spirit's gifts for service today",
        body="""Many Baptists have taught that the miraculous "sign" gifts in this list (tongues, prophecy as new revelation, and gifts of healing and miracles) had a special purpose in the apostles' time: to confirm the gospel message before the New Testament was complete (Hebrews 2:3-4; 2 Corinthians 12:12). The church is built on the foundation of the apostles and prophets (Ephesians 2:20), and Scripture is now our complete guide. The Spirit still works powerfully. Every believer receives him at conversion (1 Corinthians 12:13) and is given gifts for service, such as teaching, encouraging, giving, leading, helping and showing mercy (Romans 12:6-8). God still heals and works wonders in answer to prayer, as he wills. Baptist churches today vary, and some are open to all the gifts, but all test everything by Scripture.""",
        verses="Hebrews 2:3-4; Ephesians 2:20; 1 Corinthians 12:13; Romans 12:6-8",
        quotes=["95968 | The signs of that Spirit in those days were visible and audible.",
                "95968 | when the river first came into its bed, it came like the tide in Morecambe Bay, breast-high, with a roar and a rush. But it was quiet after that."],
        blanks=["Every believer receives the Spirit at ____. | conversion",
                "The Spirit gives gifts for ____ in every church. | service"],
        note="Alexander Maclaren, the Baptist preacher, uses the picture of a river: it came in with a roar at Pentecost and then flowed quietly. Note that Maclaren also cautions that 1 Corinthians 13:8 (\"tongues, they shall cease\") is about the life to come rather than a date in church history; Baptists who hold that the sign gifts ceased usually rest their case on Hebrews 2:3-4 and Ephesians 2:20.",
        q2=("Why have many Baptists believed the miraculous sign gifts belonged especially to the apostles' time?",
            "Because Scripture describes them as signs confirming the apostles' message (Hebrews 2:3-4; 2 Corinthians 12:12) and the church is built on the apostolic foundation (Ephesians 2:20), now given to us in the completed Scriptures."),
        application="Ask God to show you the gifts he has given you for serving others, and ask two Christian friends what they see in you. Choose one way to use your gift this week in your church or community.",
        prayer="Holy Spirit, thank you for living in every believer and for giving us gifts to serve one another. Help us honour Jesus as Lord, use our gifts in love, and build up your church. Keep us faithful to your word in all things. Amen."),
    "wesleyan": dict(
        big_idea="The one Spirit gives every believer gifts for the common good; Wesleyans emphasize the Spirit's work of holy love, and are open to the extraordinary gifts while valuing the fruit of the Spirit above them.",
        heading="Seek the gifts that build up, and the love that matters most",
        body="""Wesleyans emphasize above all the Spirit's work of making believers holy and filling their hearts with love for God and neighbour (Galatians 5:22-23). Paul tells the church to "covet earnestly the best gifts" (12:31) and to "desire spiritual gifts" (14:1), especially those that build up the church. John Wesley believed the extraordinary gifts had become rare mainly because the church had grown cold and formal, not because God had withdrawn them, and he did not rule them out. Methodists today hold a range of views: many expect the Spirit to work mostly through ordinary gifts of service, while a charismatic stream welcomes the extraordinary gifts. All agree that gifts without love are nothing.""",
        verses="1 Corinthians 12:31; 1 Corinthians 14:1, 12; Galatians 5:22-23; Acts 2:17-18",
        quotes=["43810 | We should earnestly desire spiritual gifts",
                "43821 | seek that ye may get those by which ye may excel in edifying the Church."],
        blanks=["Covet earnestly the best ____. | gifts",
                "The Spirit's greatest work is filling us with holy ____. | love"],
        note="Adam Clarke, the Methodist commentator, treats tongues in 1 Corinthians 14 as a real supernatural gift to be regulated for the church's edification, and urges believers to seek the gifts that build up the church most.",
        q2=("Why do Wesleyans put the fruit of the Spirit (love, joy, peace ...) ahead of the extraordinary gifts?",
            "Because Paul says that gifts without love are nothing (1 Corinthians 13:1-3); the Spirit's central work is holiness of heart and life."),
        application="Pray this week for the Holy Spirit to fill you with love for God and others, and ask him which gifts he would have you use to build up your church. Read Galatians 5:22-23 each day and ask where the Spirit is growing his fruit in you.",
        prayer="Holy Spirit, fill us with your love. Make us holy in heart and life. We desire the gifts that build up your church; give them as you will, and help us use them in love for the glory of Jesus Christ. Amen."),
    "reformed": dict(
        big_idea="The one Spirit gives every believer gifts for the common good; the Reformed tradition holds that the revelatory and miraculous gifts served the apostles' founding age, while the Spirit now works through the completed Scriptures.",
        heading="The Spirit speaks in the completed Scriptures",
        body="""The historic Reformed view is that the revelatory and miraculous gifts listed here (prophecy, tongues and their interpretation, miracles and gifts of healing) belonged to the founding age of the church. God gave them to confirm the apostles' message (Hebrews 2:3-4; 2 Corinthians 12:12) while the New Testament was being written. God has now spoken finally in his Son (Hebrews 1:1-2), and the Scriptures are complete and sufficient (2 Timothy 3:16-17); the Westminster Confession says God's former ways of revealing his will are "now ceased." This does not mean the Spirit is inactive. He gives every believer gifts for teaching, serving, giving and leading; he illumines the Scriptures; and God hears prayer for the sick and heals as he wills. Some Reformed Christians today believe the gifts continue.""",
        verses="Hebrews 1:1-2; Hebrews 2:3-4; Ephesians 2:20; 2 Timothy 3:16-17",
        quotes=["24652 | namely, extraordinary offices and powers, bestowed on ministers and Christians in the first ages, for conviction of unbelievers, and propagation of the gospel."],
        blanks=["God hath in these last days spoken unto us by his ____. | Son",
                "The Scriptures are complete and ____ for faith and life. | sufficient"],
        note="Matthew Henry describes the gifts of 1 Corinthians 12 as \"extraordinary offices and powers, bestowed ... in the first ages.\" For honesty, note that Albert Barnes, also Presbyterian, reads \"tongues, they shall cease\" (13:8) as referring to the life to come rather than the end of the apostolic age; the Reformed case rests mainly on Hebrews 1-2 and Ephesians 2:20.",
        q2=("Why does the Reformed tradition connect the miraculous gifts with the apostles' time?",
            "Because Scripture presents them as signs confirming the apostolic message (Hebrews 2:3-4; 2 Corinthians 12:12), and God's revelation is now complete in Christ and the Scriptures (Hebrews 1:1-2)."),
        application="Spend time each day this week in the Scriptures, asking the Spirit to open your understanding. Ask God which ordinary gifts of service he has given you, and use one to build up others in your church.",
        prayer="Spirit of truth, thank you for the Scriptures, God's complete and sufficient word. Open our eyes to understand them, and give us gifts to serve one another in love. Keep us honouring Jesus Christ as Lord, to the glory of God. Amen."),
    "lutheran": dict(
        big_idea="The one Spirit gives every believer gifts for the common good; Lutherans teach that the Spirit works chiefly through the Word and Sacraments, and test every claimed experience by the Word.",
        heading="The Spirit comes through the Word and Sacraments",
        body="""Lutherans teach that the Holy Spirit is given through the means God has appointed: the preaching of the Word and the Sacraments. Through these he creates faith and keeps us in it (Romans 10:17). Luther warned against "enthusiasts" who claimed that the Spirit spoke to them directly, apart from or above Scripture. Extraordinary gifts are not denied as impossible, but they are not expected as the normal Christian life, they are not signs of a higher class of Christians, and they must never be set beside or above the Word. God gives all believers gifts to serve their neighbours in their callings. Christians pray for the sick and trust God's good will. Since the 1960s a charismatic movement has existed among some Lutherans, but this is not the church's historic teaching.""",
        verses="Romans 10:17; 1 Corinthians 14:33, 40; 2 Timothy 3:16-17; Luke 16:29-31",
        quotes=["97146 | For through the Word and Sacraments, as through instruments, the Holy Ghost is given, who works faith",
                "97123 | It is through the Word of God and the Sacraments that the Holy Spirit does His work in us."],
        blanks=["Faith cometh by hearing, and hearing by the ____ of God. | word",
                "The Holy Ghost is given through the Word and ____. | Sacraments"],
        note="The first quotation is Article V of the Augsburg Confession (1530); the second is from Joseph Stump's explanation of Luther's Small Catechism. In the Small Catechism, Luther confesses that \"the Holy Ghost has called me through the Gospel, enlightened me by His gifts.\"",
        q2=("Why do Lutherans insist that the Spirit works through the Word and Sacraments?",
            "Because Scripture ties the Spirit's work to God's Word (Romans 10:17) and promises; this gives certainty, so faith rests on God's promise rather than on feelings or claimed private revelations."),
        application="Be present for the Word and Sacrament this Sunday, expecting the Holy Spirit to work through them. Each day, read a portion of Scripture and pray Luther's explanation of the Third Article, thanking God that the Spirit has called you by the Gospel.",
        prayer="Holy Spirit, you call, gather and enlighten your church through the Gospel. Keep us in the true faith through your Word and Sacraments. Give us gifts to serve our neighbours, and keep us from trusting anything above your Word. Amen."),
    "pentecostal": dict(
        big_idea="The one Spirit gives every believer gifts for the common good; Pentecostals teach that all these gifts continue today and that believers should seek the baptism in the Holy Spirit, with speaking in tongues.",
        heading="All the gifts are for today",
        body="""Pentecostals believe that every gift in this list (wisdom, knowledge, faith, healing, miracles, prophecy, discerning of spirits, tongues and interpretation) is for the church today, because nothing in Scripture says they would cease before Christ returns. On the day of Pentecost Peter said the promise of the Spirit was "unto you, and to your children, and to all that are afar off" (Acts 2:39). Classical Pentecostals teach a baptism in the Holy Spirit, distinct from and usually after conversion, which gives power for witness (Acts 1:8). In Acts it is marked by speaking in other tongues (Acts 2:4; 10:46; 19:6). Believers are encouraged to seek it, to pray for the sick expecting God to heal, and to use every gift in love and good order.""",
        verses="Acts 1:8; Acts 2:4, 38-39; Acts 10:44-46; Acts 19:1-6; Mark 16:17-18",
        quotes=["98620 | When you have the full baptism of the Holy Spirit you are satisfied.",
                "98620 | His blessed Presence will permeate your whole being"],
        blanks=["The promise is unto you, and to your children, and to all that are ____ off. | afar",
                "Ye shall receive ____, after that the Holy Ghost is come upon you. | power"],
        note="Carrie Judd Montgomery, a teacher on divine healing who was baptized in the Spirit in 1908, wrote these words in her chapter \"The Promise of the Father.\" The wider charismatic movement welcomes all the gifts but does not always teach tongues as the necessary first sign of Spirit baptism.",
        q2=("Why do Pentecostals believe the baptism in the Holy Spirit is a distinct experience after conversion?",
            "Because in Acts believers who already followed Christ later received the Spirit's fullness with outward signs (Acts 2:4; 8:14-17; 19:1-6), and Jesus promised power for witness (Acts 1:8)."),
        application="Spend time this week asking God to fill you with his Holy Spirit (Luke 11:13). Ask him which gifts he wants to give or stir up in you, and use them in love to build up others. Pray in faith for someone who is sick.",
        prayer="Holy Spirit, we thank you for the promise of the Father, poured out on all flesh. Fill us afresh with your power and presence. Give us your gifts as you will, and help us use them in love and good order, to exalt Jesus as Lord. Amen."),
}


def write(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(text)


body = HEAD.format(code="spiritual-gifts", version="all_views",
                   big_idea="The one Spirit gives every believer gifts for the common good and leads us to confess Jesus as Lord; Christians share this while differing honestly over whether the extraordinary gifts continue today.")
body += "\n" + SHARED.format(m1=6, m2=6) + "\n" + POINT3_SHARED + "\n" + DIFFER.format(md=8)
questions = "\n".join([Q1,
    "q: Why do sincere Christians reading the same chapter reach different conclusions about tongues, prophecy and healing today? | Scripture does not state directly when or whether these gifts would cease; Christians weigh texts such as Hebrews 2:3-4 and Ephesians 2:20 against Acts 2:39 and 1 Corinthians 14 differently, and their churches' experience differs.",
    Q_GRACE, Q_SERVE])
body += "\n" + CLOSE.format(mq=5, questions=questions,
    application="Find out what your own church teaches about spiritual gifts and why. Ask God to show you the gifts he has given you, and use one this week to serve others in love. Pray for unity among Christians who see this question differently.",
    prayer="Holy Spirit, thank you for giving gifts to your church and for leading us to confess Jesus as Lord. Help us use every gift you give in love and for the common good. Where your people differ, give us humility, patience and a shared desire to honour Christ. Amen.")
write("spiritual-gifts.txt", body)

for code, t in TRADITIONS.items():
    body = HEAD.format(code=f"spiritual-gifts--{code}", version=f"tradition:{code}", big_idea=t["big_idea"])
    body += "\n" + SHARED.format(m1=7, m2=7) + "\n"
    body += f"== point | 9 | {t['heading']}\n{t['body']}\nverses: {t['verses']}\n"
    body += "".join(f"quote: {q}\n" for q in t["quotes"])
    body += "".join(f"blank: {b}\n" for b in t["blanks"])
    body += f"note: {t['note']}\n\n"
    body += DIFFER.format(md=0)
    questions = "\n".join([Q1, f"q: {t['q2'][0]} | {t['q2'][1]}", Q_SERVE, Q_GRACE])
    body += "\n" + CLOSE.format(mq=6, questions=questions, application=t["application"], prayer=t["prayer"])
    write(f"spiritual-gifts--{code}.txt", body)
print("wrote spiritual-gifts family")
