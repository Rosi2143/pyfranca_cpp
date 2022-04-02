{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) -}}
enum class {{ item.name }} {
    {%- for eo in item.enumerators.values() %}
        {{ doxygen.add_inline_comment(eo) -}}
        {{ render_enumerator(eo) -}}
    {%- endfor %}
};


