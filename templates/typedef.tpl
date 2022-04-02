{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) }}
typedef {{ render_type(item) }} {{ item.name }};


