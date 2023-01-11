// 导入所有组件
const body_div = document.createElement("div");
[
"normal-card/index.html",
"custom-img/index.html",
"media-slide/index.html",
"custom-chips/index.html",
]
.forEach((name) => {
    const my_wc = document.createElement("div");
    $(my_wc).load("../static/components/" + name);
    body_div.appendChild(my_wc);
})
document.body.appendChild(body_div);