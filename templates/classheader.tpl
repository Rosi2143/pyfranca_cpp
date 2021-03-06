{% import 'macros/doxygen.tpl' as doxygen %}
#pragma once
// Generated from Franca IDL Interface {{ fqn }}
// {{ timestamp }}

{{ boilerplate }}

#include "i{{name}}.h"

class {{ name }}: public i{{ name }}
{
    public:
        {{ name }} ();
        {{ name }} (const {{ name }} & c);
        {{ name }} & operator=(const {{ name }} & c);
        ~{{ name}} ();

    {% for m in item.methods.values() %}
    {{ doxygen.add_function_comment(m, m.in_args, m.out_args) -}}
    void {{ m.name }} (
                        {% set maybecomma = joiner(",") %}
                        {%- for p in m.in_args.values() -%}
                           {{ maybecomma() }} {{ render_type(p) }} {{ p.name }}{% endfor %}
                        {%- for p in m.out_args.values() -%}
                           {{ maybecomma() }} {{ render_type(p) }} &{{ p.name }}{% endfor %}
                      );
    {%endfor%}

  private:
    // none
};

