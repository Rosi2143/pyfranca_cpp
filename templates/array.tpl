{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) }}
typedef std::vector<{{ render_type(item) }}> {{ item.name }};
