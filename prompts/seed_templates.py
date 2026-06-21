SEED_TEMPLATES = [
    {
        "name": "概念辨析追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,案例分析",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
错因：{mistake_reason}

请围绕这个易混概念连续追问。先让学生分别给出两个概念的定义，再追问区别标准、典型陷阱和案例判断。每次只问一个问题，不要一次性给答案。""",
        "default_goal": "让学生能清楚区分易混概念，并能在案例事实中正确适用。",
        "end_condition": "学生能独立说出定义、区别标准、反例和考试表达。",
    },
    {
        "name": "构成要件追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,论述,案例分析",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
掌握度：{mastery_level}

请按构成要件展开追问。先问定义，再问主体、客体或权利基础、主观方面、客观方面、法律效果和例外。学生答不全时，把问题拆小。""",
        "default_goal": "让学生能按考试需要完整拆出构成要件。",
        "end_condition": "学生能不看答案说出主要要件，并能解释每个要件的作用。",
    },
    {
        "name": "案例分析追问",
        "subject_scope": "通用",
        "question_type_scope": "案例分析,单选,多选",
        "body": """题干：{question_text}
参考答案：{reference_answer}

请把题干拆成事实、争点、规则、适用、结论五步追问。不要先给结论，先让学生识别关键事实。""",
        "default_goal": "训练从事实到法律规则再到结论的分析路径。",
        "end_condition": "学生能独立完成事实筛选、争点定位、规则适用和结论表达。",
    },
    {
        "name": "主观题采分追问",
        "subject_scope": "通用",
        "question_type_scope": "简答,论述,案例分析",
        "body": """当前考点：{knowledge_point}
参考答案：{reference_answer}

请按法硕主观题采分逻辑追问：定义、要件、展开、适用、结论。先让学生口述答案，再指出缺失采分点，并继续追问补齐。""",
        "default_goal": "让学生形成能拿分的主观题表达结构。",
        "end_condition": "学生能给出结构完整、术语准确、结论明确的答案。",
    },
    {
        "name": "考前速记追问",
        "subject_scope": "通用",
        "question_type_scope": "单选,多选,简答,论述",
        "body": """当前科目：{subject}
当前考点：{knowledge_point}
近期薄弱点：{recent_weaknesses}

请用高频短问答检查背诵漏洞。每个问题应短、准、可立即回答。学生答错时给一个记忆钩子，然后继续问。""",
        "default_goal": "快速暴露背诵漏洞并形成短时复习清单。",
        "end_condition": "学生连续正确回答 5 个关键短问。",
    },
    {
        "name": "错因修复追问",
        "subject_scope": "通用",
        "question_type_scope": "通用",
        "body": """错因：{mistake_reason}
当前考点：{knowledge_point}
学生备注：{notes}

请专门围绕错因追问。先让学生复盘为什么错，再追问正确判断路径，最后让学生用一句话写出防错规则。""",
        "default_goal": "把一次错误转化成可复用的防错规则。",
        "end_condition": "学生能说出错误原因、正确路径和防错提醒。",
    },
]
