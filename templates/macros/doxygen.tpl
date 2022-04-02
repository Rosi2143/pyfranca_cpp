{% macro get_comment(item) -%}
{% if item.comments['@description'] is defined -%}
{{- item.comments['@description'] -}}
{% else %} documentation does not exist {% endif%}
{%- endmacro -%}


{% macro add_inline_comment(item) -%}
/**< {{- get_comment(item) }} */
{% endmacro %}


{% macro add_function_comment(item, in_args=[], out_args=[], return='') -%}
/**
  * @brief {{ get_comment(item) }}
  *
{%- if in_args|length %}
{%- for p in in_args.values() %}
  * @param[in] {{ p.name }} {{ get_comment(p) -}}
{% endfor -%}
{%- endif -%}
{%- if out_args|length %}
{%- for p in out_args.values() %}
  * @param[out] {{ p.name }} {{ get_comment(p) -}}
{% endfor -%}
{%- endif -%}
{% if return|length %}
  * @return {{ return -}}
{% endif %}
  */
{%- endmacro -%}