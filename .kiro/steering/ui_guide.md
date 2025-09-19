We will always use Django templates.
While using django templates we will be using django-cotton
This means no {% extends %} and {% with %} and {% block %} tags. 
We must use <c-layout> or some other layout file from the app level. the slot will replace the content we write inside. this is exactly or almost the same as reactjs and other modern component suites of UI.

We will be using tailwindcss for styling so never write custom css

---

### Components

* **`{{ slot }}`**
  Default content:

  ```html
  <!-- cotton/box.html -->
  <div class="box">{{ slot }}</div>
  <!-- usage -->
  <c-box>…</c-box>
  ```

* **Attributes**
  Pass strings or variables:

  ```html
  <c-weather temperature="23" unit="{{ unit }}" condition="windy"/>
  ```

* **Named Slots**
  For HTML payloads:

  ```html
  <c-weather-card day="Tue">
    <c-slot name="icon">…</c-slot>
    <c-slot name="label">…</c-slot>
  </c-weather-card>
  ```

* **Dynamic (`:`) Attributes**
  Inject context values or types:

  ```html
  <c-weather :today="today_obj"/>
  <c-mycomp :items="['a','b']" :count="1" :flag="None"/>
  ```

* **`{{ attrs }}` & `:attrs`**
  Reflect all HTML attributes or merge a dict:

  ```html
  <!-- component -->
  <input {{ attrs }}/>
  <!-- usage -->
  <c-input name="x" placeholder="…" readonly/>
  <c-input :attrs="widget_attrs" required/>
  ```

* **`<c-vars />`**
  Define defaults (excluded from `attrs`):

  ```html
  <c-vars type="success"/>
  <div class="{% if type=='success'%}…">{ slot }</div>
  ```

* **Boolean Attributes**
  Presence = `True`:

  ```html
  <c-input name="tel" required/>
  ```

* **Dynamic Components**
  Render by name:

  ```html
  <c-component is="icons.{{ icon_name }}"/>
  <c-component :is="comp_var"/>
  ```

* **Context Isolation**
  `only` attribute limits context to passed props.

* **Alpine.js**

  * Access `x-data` via `{{ x_data }}`
  * Use `::` to preserve `:` in `{{ attrs }}` (e.g. `::x-bind`)

---

### Template Layout

```
templates/
│
├─ cotton/<app>/       ← reusable components
│   └─ component.html
│
└─ <app>/             ← full-page templates
    └─ page.html
```

* **Naming**: `<c-app.component>` (dot notation).
* **Pages** import from `templates/cotton`; components don’t import pages.
