{% import 'macros/doxygen.tpl' as doxygen %}
{{ doxygen.add_inline_comment(item) }}
union {{ item.name }} {
    {%- for f in item.fields.values() %}
        {{ render_type(f) }} {{ f.name }}; {% endfor %}
};

{# TODO: extends, reference, flags  #}

