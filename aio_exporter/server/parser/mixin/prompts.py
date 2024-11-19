from langchain.prompts import PromptTemplate

# 根据一个 markdown 的上下文
# 判断里面所有出现过的图片是否和上下文相关
# 如果一个图片被删除,并不影响上下文内容的表达,认为这个图片内容和上下文不相关

FIND_USEFUL_IMAGES = """
<system>
你是一个资深的微信公众号文章编辑，现在你需要评估给定的公众号上下文中的图片是否可以被删除

<user>
仔细分析如下的公众号文章
如果一个图片不包含任何文字,且被删除,并不影响上下文内容的表达,认为这个图片内容可以被删除

<markdown>
{{context}}
</markdown>

</user>

请对上文当中出现的 {{ n }} 张图片进行分析，并按照如下json格式返回 
```json
[
    {"是否包含文字": ... , "理由": "解释为什么可删除/应保留" , '图片1': "可删除/应保留"},
    ...
]
```

"""

EXTRACT_RELATED_INFORMATION = """
<system>
你是一个资深的微信公众号文章编辑，现在你需要评估给定的公众号上下文中的图片是否可以被删除

<user>
仔细分析如下的公众号文章当中涉及到的图片,并基于上下文分析可以图片当中存在哪些要点
你所给出的要点需要和上下文紧密相关,能够补充上下文所需要的图片信息

<markdown>
{{context}}
</markdown>

</user>

请对上文当中出现的 {{ n }} 张图片进行分析，并按照如下json格式返回 
```json
[
    {'图片编号': "1" , "要点": [...]},
    ...
]
```

"""


def create_prompt_template(template_string):
    return PromptTemplate.from_template(template_string, template_format="jinja2")


