{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) -}}
struct {{ item.name }} {
    {%- for f in item.fields.values() %}
        {{ doxygen.add_inline_comment(f) -}}
        {{ render_type(f) }} {{ f.name }}; {% endfor %}
};
{# TODO: extends, reference, flags  #}

