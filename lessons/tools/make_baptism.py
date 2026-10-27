"""Writes the Baptism lesson family (all-views + one version per approved tradition) into lessons/source/.
The shared sections are written once here so every version teaches the common ground identically."""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "source")

HEAD = """code: {code}
family: baptism
version: {version}
issue: baptism
title: Baptized into Christ
big_idea: {big_idea}
topic: Baptism
also: Jesus, the Christ; Regeneration; Church
audience: adults
minutes: 45
translation: KJV
passage: Matthew 28:18-20; Romans 6:3-4
"""

OPENING = """== opening | 4
Ask the class, if they are comfortable sharing: "Do you remember your baptism, or have you been told about it? What do you remember, or what were you told?" Some will remember a river or a baptistry; others were baptized as babies and have only photographs. Some may not have been baptized at all. Explain that baptism is something Jesus commanded, and today we look at what it means.
note: Be gentle with anyone who has not been baptized or whose experience differs from the class's. The goal is understanding, not embarrassment.

== scripture | 3
Read both passages aloud: first Jesus' command (Matthew 28:18-20), then Paul's explanation of what baptism means (Romans 6:3-4).

== background | 5
Matthew 28:18-20, often called the Great Commission, are Jesus' last words in Matthew's Gospel. With all authority in heaven and earth, he sends his followers to make disciples of all nations, "baptizing them in the name of the Father, and of the Son, and of the Holy Ghost," and teaching them to obey all he commanded.

In Romans 6 Paul answers a question: if we are saved by grace, should we keep on sinning? His answer points to baptism. Those baptized into Christ were baptized into his death, and they are to walk in "newness of life." Christians in every tradition treasure these verses, even where they understand baptism's details differently.
"""

POINT1 = """== point | {m1} | Commanded by Christ for his disciples
Baptism was not invented by the church. Jesus himself commanded it, as part of making disciples of all nations, in the name of the Father, the Son and the Holy Spirit. Christians of every tradition baptize because Jesus told us to, and they use these words.
verses: Matthew 28:18-20; Acts 2:41; Acts 8:12
quote: 97127 | Baptism consists in applying water to a person "in the name of the Father and of the Son and of the Holy Ghost," as Christ has commanded.
blank: Baptize them in the name of the Father, and of the Son, and of the Holy ____. | Ghost (Spirit)
blank: Christians baptize because ____ commanded it. | Jesus
"""

POINT2 = """== point | {m2} | Baptized into Christ's death and resurrection
Paul says that "so many of us as were baptized into Jesus Christ were baptized into his death" (Romans 6:3). Baptism is about union with Christ: belonging to him, sharing in what his death and resurrection accomplished, and being marked as his.
verses: Romans 6:3-4; Galatians 3:27; Colossians 2:12
quote: 67769 | sealed with the seal of heaven, and as it were formally entered and articled, to all the benefits and all the obligations of Christian discipleship
quote: 43228 | To be baptized into Christ, is to receive the doctrine of Christ crucified
blank: So many of us as were baptized into Jesus Christ were baptized into his ____. | death
blank: Baptism speaks of our ____ with Christ. | union
"""

POINT3_SHARED = """== point | 4 | Called to walk in newness of life
Baptism looks forward as well as back. "Like as Christ was raised up from the dead by the glory of the Father, even so we also should walk in newness of life" (Romans 6:4). Whatever our tradition, the baptized are called to live as people who belong to the risen Christ.
verses: Romans 6:4-11; 2 Corinthians 5:17; Colossians 3:1-3
quote: 50573 | by our very profession made in baptism we have renounced sin, and have pledged ourselves to live to God.
blank: We also should walk in ____ of life. | newness
blank: The baptized are called to live as people who belong to the risen ____. | Christ
"""

DIFFER = """== differ | {md} | Where Christians differ
Christians agree that Jesus commanded baptism, that it is done with water in the name of the Father, Son and Holy Spirit, that it is linked with repentance, faith, forgiveness and union with Christ, and that true baptism is not repeated. They differ on three questions: who should be baptized (believers only, or also the children of believers), how (immersion, or also pouring and sprinkling), and what baptism does (a means through which God gives grace, a sign and seal of his covenant, or an act of obedience that testifies to grace already received). Here are the main views of the five traditions, each described as its own teachers describe it. Sincere, Bible-believing Christians hold each of them.
view: baptist
view: wesleyan
view: reformed
view: lutheran
view: pentecostal
note: Encourage the class to describe other traditions' views as their own members would. Many Christians from these traditions worship and serve together and recognise one another as brothers and sisters in Christ.
"""

CLOSE = """== questions | {mq}
{questions}

== application | 2
{application}

== prayer | 2
{prayer}
"""

PRAYER_ALL = ("Lord Jesus, you commanded your church to make disciples and baptize them in the name of the Father, the Son and "
              "the Holy Spirit. Thank you for uniting us to yourself in your death and resurrection. Help us walk in newness of "
              "life. Where your people understand baptism differently, give us humility, love and a shared desire to be "
              "faithful to your word. Amen.")

TRADITIONS = {
    "baptist": dict(
        big_idea="Jesus commanded baptism for his disciples; it pictures our union with Christ in his death and resurrection, and Baptist churches baptize believers by immersion as their public confession of faith.",
        heading="Baptism follows faith",
        body="""In the New Testament, people heard the gospel, believed, and were baptized: "they that gladly received his word were baptized" (Acts 2:41), and the Ethiopian official went "down both into the water" with Philip after confessing his faith (Acts 8:36-38). Baptist churches therefore baptize those who personally repent and trust in Christ, and they baptize by immersion, which pictures being buried with Christ and raised to new life. Baptism does not save us; Christ does. Baptism is the believer's public "yes" to Jesus, an act of obedience and a confession before the church and the world. Children are dedicated, taught and prayed for, and baptized when they personally trust Christ.""",
        verses="Acts 2:41; Acts 8:36-38; Romans 6:4; Colossians 2:12",
        quotes=["96422 | The correct text in Mark 1: 10 is 'out of,' and does show that he had been in the water; and so in Acts 8: 39.",
                "50574 | It is altogether probable that the apostle in this place had allusion to the custom of baptizing by immersion."],
        blanks=["Baptism follows personal ____ in Christ. | faith",
                "Immersion pictures being ____ and raised with Christ. | buried"],
        note="Broadus, the Baptist commentator, notes the wording of Mark 1:10 and Acts 8:39. Barnes, a Presbyterian who did not require immersion, still judged that Paul was probably alluding to it in Romans 6:4.",
        q2=("Why do Baptist churches wait until a person can personally profess faith before baptizing?",
            "Because in the New Testament baptism follows hearing, repentance and belief (Acts 2:41; 8:36-38); baptism is the believer's own confession."),
        application="If you have trusted Christ but have not yet been baptized, talk with your pastor this week. If you have been baptized, remember it as your public \"yes\" to Jesus, and ask how you can walk in newness of life this week.",
        prayer="Lord Jesus, thank you that you died, were buried and rose again for us. Thank you for the picture of baptism: buried with you and raised to walk in newness of life. Help all who trust you to follow you in baptism, and help all the baptized to live as people who belong to you. Amen."),
    "wesleyan": dict(
        big_idea="Jesus commanded baptism for his disciples; Methodist and Wesleyan churches receive it as a sacrament, a sign and means of God's grace for believers and their children, calling each to personal faith and new life.",
        heading="Baptism: a sign and means of God's grace",
        body="""Methodist and Wesleyan churches receive baptism as a sacrament: an outward and visible sign of an inward and spiritual grace, through which God works. It marks our entry into God's covenant people, the church. Because God's promise is "unto you, and to your children" (Acts 2:39), and because Jesus welcomed little children (Mark 10:13-16), children of Christian families are baptized, as are adults who come to faith. Water is usually poured or sprinkled. John Wesley taught that baptism is linked with the new birth, but he insisted that every baptized person must still personally turn to Christ and be born of the Spirit. Baptized children are taught the faith and later confirm it for themselves.""",
        verses="Acts 2:38-39; Mark 10:13-16; Titus 3:5; Colossians 2:11-12",
        quotes=["40375 | But, certainly, no argument can be drawn from this concession against the baptism of children.",
                "42271 | Take on you the public profession of the religion of Christ, by being baptized in his name"],
        blanks=["Baptism is an outward sign of an inward ____. | grace",
                "Baptized children must later ____ Christ for themselves. | trust (confess)"],
        note="Adam Clarke, the Methodist commentator, writes on Matthew 28:19 that the order \"teach, then baptize\" for adult converts does not argue against baptizing the children of believers.",
        q2=("Why do Methodist churches baptize the children of believing families?",
            "Because God's promise is to believers and their children (Acts 2:39), Jesus welcomed children (Mark 10:14), and baptism is God's gracious sign of welcome into his covenant people; the child is then raised to trust Christ personally."),
        application="If you were baptized as a child, thank God this week for his grace shown to you before you could ask for it, and renew your own commitment to Christ in prayer. If you have children or grandchildren, pray for them to come to living faith.",
        prayer="Gracious God, thank you for the gift of baptism, the sign of your grace and of our welcome into your family. Renew in us the faith our baptism calls for. Help us and our children to know Christ personally and to walk in newness of life. Amen."),
    "reformed": dict(
        big_idea="Jesus commanded baptism for his disciples; Presbyterian and Reformed churches receive it as the sign and seal of God's covenant of grace, given to believers and their children.",
        heading="Baptism: the sign and seal of God's covenant",
        body="""Presbyterian and Reformed churches teach that baptism is a sacrament, a sign and seal of God's covenant of grace. In the Old Testament, God gave circumcision as the covenant sign to Abraham and his children (Genesis 17:7-12). In the New Testament, baptism takes its place (Colossians 2:11-12), and the promise is still "unto you, and to your children" (Acts 2:39). So believers are baptized, and so are their children; whole households were baptized when parents believed (Acts 16:15, 33). Sprinkling or pouring is usual. Baptism does not automatically make anyone a Christian: the grace it signifies is received by faith, and the baptized child is raised to trust Christ personally.""",
        verses="Genesis 17:7; Colossians 2:11-12; Acts 2:39; Acts 16:14-15; 1 Corinthians 7:14",
        quotes=["47483 | And so, too, the question respecting infant baptism is not so much whether a parent OUGHT to devote his children to God in this ordinance, as whether he MAY do it.",
                "68109 | Infant baptism tacitly superseded infant circumcision"],
        blanks=["Baptism is a sign and ____ of God's covenant. | seal",
                "The promise is unto you, and to your ____. | children"],
        note="Albert Barnes, the Presbyterian commentator, calls presenting children for baptism \"an inestimable privilege.\" Interestingly, he also cautions (on Acts 2:39) that that verse should not be used on its own as proof of infant baptism; the Reformed case rests on the whole covenant pattern of Scripture.",
        q2=("Why do Reformed churches connect baptism with circumcision?",
            "Both are signs of God's one covenant of grace; circumcision was given to believers' children, and Colossians 2:11-12 links the two, so baptism is also given to believers' children."),
        application="If you were baptized as a child, thank God this week for his covenant faithfulness to you and your family, and make sure your own faith rests on Christ. If you have children or grandchildren, pray for them by name as children of the covenant.",
        prayer="Faithful God, you keep covenant with your people and their children. Thank you for the sign and seal of baptism. Help us trust in Christ, the one baptism points to, and raise our children to know and love you. Amen."),
    "lutheran": dict(
        big_idea="Jesus commanded baptism for his disciples; Lutheran churches receive it as God's gift, water joined to his Word, through which he gives forgiveness and new life to all who believe, including little children.",
        heading="Baptism: God's gift through water and the Word",
        body="""Lutheran churches teach that baptism is not simply water, but water joined to God's command and promise. Through it God himself acts: he forgives sins, rescues from death and the devil, and gives eternal salvation to all who believe his promise (Mark 16:16; Titus 3:5). Baptism is God's work for us more than our work for him. Faith receives what baptism gives, and God works faith even in little children through his Word, so children are baptized. Water is usually poured. Luther taught that the Christian life is a daily return to baptism: dying to sin in repentance and rising to new life in faith.""",
        verses="Mark 16:16; Titus 3:5; Acts 2:38-39; 1 Peter 3:21",
        quotes=["96989 | faith alone makes the person worthy to receive profitably the saving, divine water.",
                "97150 | Of Baptism they teach that it is necessary to salvation, and that through Baptism is offered the grace of God, and that children are to be baptized who, being offered to God through Baptism are received into God's grace."],
        blanks=["Baptism is not simply water, but water joined with God's ____. | Word",
                "Faith ____ the gift God gives in baptism. | receives"],
        note="The second quotation is Article IX of the Augsburg Confession (1530), the chief confession of the Lutheran churches. The Small Catechism (in the edition in our library) asks, \"What gifts or benefits does Baptism confer?\" and answers: \"It works forgiveness of sins, delivers from death and the devil, and confers everlasting salvation\" on all who believe God's promise.",
        q2=("What do Lutherans mean by calling baptism a \"means of grace\"?",
            "God uses baptism, water joined to his Word, to give forgiveness and new life; it is God's action and gift, received by faith."),
        application="Each morning this week, as you wash your face, remember your baptism, as Luther suggested: thank God that you belong to him, confess your sins, and rise to live the new life he gives.",
        prayer="Heavenly Father, thank you that in baptism you have washed us, forgiven us and made us your children through water and your Word. Help us return to our baptism daily, dying to sin and rising to new life in Christ. Amen."),
    "pentecostal": dict(
        big_idea="Jesus commanded baptism for his disciples; Pentecostal churches baptize believers by immersion as an act of obedience and testimony, and look also for the promised gift of the Holy Spirit.",
        heading="Water baptism: obedience, testimony, and the promise of the Spirit",
        body="""Most Pentecostal churches baptize believers by immersion. Water baptism follows salvation: those who have repented and trusted Christ are "buried with him by baptism" (Romans 6:4) as an act of obedience and a public testimony. It does not save; Christ saves. Infants are dedicated to the Lord, and baptized when they believe. Peter's sermon also points beyond water baptism: "Repent, and be baptized ... and ye shall receive the gift of the Holy Ghost" (Acts 2:38). Pentecostals encourage every believer to seek that promised fullness of the Spirit, which they call the baptism in the Holy Spirit.""",
        verses="Acts 2:38-39; Acts 8:36-38; Romans 6:4; Acts 19:4-6",
        quotes=["98328 | bury the candidates in a watery grave by immersion",
                "43229 | It is probable that the apostle here alludes to the mode of administering baptism by immersion"],
        blanks=["Water baptism is an act of ____ and testimony. | obedience",
                "Repent, and be baptized, and ye shall receive the gift of the Holy ____. | Ghost (Spirit)"],
        note="Maria Woodworth-Etter, the early Pentecostal evangelist, describes baptizing converts by immersion in rivers before large crowds. The baptism in the Holy Spirit is the subject of the separate lesson on spiritual gifts.",
        q2=("Why do Pentecostal churches baptize believers by immersion?",
            "Because in the New Testament baptism follows repentance and faith (Acts 2:38-41; 8:36-38), and immersion pictures burial and resurrection with Christ (Romans 6:4)."),
        application="If you have trusted Christ but have not been baptized, talk with your pastor this week about being baptized. If you have been, thank God for it, and pray for a fresh filling of his Holy Spirit to live out your new life.",
        prayer="Lord Jesus, thank you that you died and rose again for us. Thank you for the picture of baptism: buried with you and raised to new life. Help every believer to follow you in obedience, and fill us with your Holy Spirit to live for you. Amen."),
}

Q1 = "q: What do all Christians agree about baptism, according to today's passages? | Jesus commanded it; it is done in the name of the Father, Son and Holy Spirit; it is linked with discipleship, faith and union with Christ; it calls us to new life."
Q_NEW = "q: What does Romans 6 say baptism should mean for the way we live this week? | We have died to sin with Christ and been raised to walk in newness of life; we live as people who belong to him."
Q_GRACE = "q: How can we hold our own convictions about baptism while showing love to Christians who practise it differently? | By being clear about what Scripture teaches as we understand it, listening carefully, describing others fairly, and remembering that we share one Lord and one faith."


def write(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(text)


# All-views version
body = HEAD.format(code="baptism", version="all_views",
                   big_idea="Jesus commanded baptism for his disciples and it speaks of our union with Christ; Christians share these truths while differing honestly over who should be baptized, how, and what baptism does.")
body += "\n" + OPENING + "\n" + POINT1.format(m1=6) + "\n" + POINT2.format(m2=6) + "\n" + POINT3_SHARED + "\n" + DIFFER.format(md=8)
questions = "\n".join([Q1,
    "q: Each tradition points to particular verses. Why do sincere Christians reading the same Bible reach different conclusions about baptism? | The New Testament does not answer every question directly (for example, whether the \"households\" in Acts included infants), so Christians weigh different texts and patterns (covenant continuity, the order of faith and baptism) differently.",
    Q_GRACE, Q_NEW])
body += "\n" + CLOSE.format(mq=5, questions=questions,
    application="This week, find out what your own church teaches about baptism and why, and look up the key texts for that view. If you have not been baptized, talk with your pastor. Pray for the unity of Christians who differ on this question.",
    prayer=PRAYER_ALL)
write("baptism.txt", body)

for code, t in TRADITIONS.items():
    body = HEAD.format(code=f"baptism--{code}", version=f"tradition:{code}", big_idea=t["big_idea"])
    body += "\n" + OPENING + "\n" + POINT1.format(m1=7) + "\n" + POINT2.format(m2=7) + "\n"
    body += f"== point | 9 | {t['heading']}\n{t['body']}\nverses: {t['verses']}\n"
    body += "".join(f"quote: {q}\n" for q in t["quotes"])
    body += "".join(f"blank: {b}\n" for b in t["blanks"])
    body += f"note: {t['note']}\n\n"
    body += DIFFER.format(md=0)
    questions = "\n".join([Q1, f"q: {t['q2'][0]} | {t['q2'][1]}", Q_NEW, Q_GRACE])
    body += "\n" + CLOSE.format(mq=6, questions=questions, application=t["application"], prayer=t["prayer"])
    write(f"baptism--{code}.txt", body)
print("wrote baptism family")
