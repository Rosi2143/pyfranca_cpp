{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) -}}
struct {{ item.name }} {
    {%- for f in item.fields.values() %}
        {{ render_type(f) }} {{ f.name }}; {{ doxygen.add_inline_comment(f) -}}
         {% endfor %}
};
{# TODO: extends, reference, flags  #}

