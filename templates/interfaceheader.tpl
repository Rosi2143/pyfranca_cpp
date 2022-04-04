{% import 'macros/doxygen.tpl' as doxygen %}
#pragma once
// Generated from Franca IDL Interface {{ fqn }}
// {{ timestamp }}

{{ boilerplate }}

#include "{{name}}.types.h"

{%- for i in imports %}
#include "{{ i.name }}.types.h"
{%- endfor %}

class i{{ name }}
{
    public:
        i{{ name }} (){};
        i{{ name }} (const i{{ name }} & c) {};
        i{{ name }} & operator=(const i{{ name }} & c){};
        virtual ~i{{ name}} (){};

    {% for m in item.methods.values() %}
    {{ doxygen.add_function_comment(m, m.in_args, m.out_args) -}}
    virtual void {{ m.name }} (
                        {% set maybecomma = joiner(",") %}
                        {%- for p in m.in_args.values() -%}
                           {{ maybecomma() }} {{ render_type(p) }} {{ p.name }}{% endfor %}
                        {%- for p in m.out_args.values() -%}
                           {{ maybecomma() }} {{ render_type(p) }} &{{ p.name }}{% endfor %}
                      ) = 0;
    {%endfor%}

  private:
    // none
};

