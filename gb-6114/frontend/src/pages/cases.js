import { api } from "../api/workbench.js";
import { errorText, field } from "../components/common/fields.js";
import { empty, pageHeading, section } from "../components/common/panel.js";
import { table } from "../components/common/table.js";
import { submit } from "../hooks/submit.js";
import { navigate } from "../router/router.js";
import { el } from "../utils/dom.js";
import { time } from "../utils/format.js";

function queueForm(config, selected) {
  const form = el("form", {class: "queue-form"},
    field(config.parameter_label, el("input", {
      name: "parameter", type: "number", min: 1, max: config.max_parameter, required: true, value: config.default_parameter,
    })),
    el("button", {type: "submit"}, "提交执行"), errorText());
  submit(form, async values => {
    const run = await api.enqueue(selected.id, {parameter: Number(values.get("parameter"))});
    navigate(`runs/${run.id}`);
  });
  return form;
}

function registration(config, selected) {
  const data = selected ? JSON.stringify(selected.payload, null, 2) : "{}";
  const form = el("form", {id: "case-form"},
    field("名称", el("input", {name: "title", required: true, minlength: 2, maxlength: 120, value: selected ? `${selected.title} · 复演` : ""})),
    field("说明", el("input", {name: "description", maxlength: 420, value: selected?.description || ""})),
    field(`${config.unit}内容`, el("textarea", {name: "payload", spellcheck: "false", required: true, rows: 12}, data),
      selected ? "可以保留演示数据，也可以编辑 JSON 后保存。" : "输入业务 JSON。"),
    errorText(), el("button", {type: "submit"}, "保存资料"));
  submit(form, async values => {
    let payload;
    try {
      payload = JSON.parse(values.get("payload"));
    } catch {
      throw new Error("资料 JSON 无法解析，请检查括号、引号和逗号");
    }
    const entry = await api.createCase({title: values.get("title"), description: values.get("description"), payload});
    navigate(`cases/${entry.id}`);
  });
  return form;
}

function bandOptions(selected, key) {
  const payload = selected.payload || {};
  const groups = [payload.calibration, payload.inspection, payload.checks]
    .filter(Array.isArray)
    .flat();
  return [...new Set(groups.map(item => item?.[key]).filter(value => typeof value === "string"))];
}

function withdrawalTable(items) {
  if (!items.length) return empty("尚未登记档位实测依据撤回。");
  return table(["重量档", "槽宽档", "撤回原因", "登记人", "登记时间"], items.map(item => [
    item.mass,
    item.slot,
    item.reason || "—",
    item.actor,
    time(item.created_at),
  ]), "已撤回的档位对");
}

function withdrawalPanel(selected, items, canWithdraw) {
  if (!selected) return null;
  const listHost = el("div", {}, withdrawalTable(items));
  const notice = el("p", {role: "status", class: "withdrawal-success"});
  const massId = `mass-options-${selected.id}`;
  const slotId = `slot-options-${selected.id}`;
  const form = el("form", {id: "withdrawal-form", class: "withdrawal-form"},
    el("div", {class: "form-grid"},
      field("重量档", el("input", {
        name: "mass", required: true, maxlength: 24, list: massId, placeholder: "例如：重档",
      })),
      field("槽宽档", el("input", {
        name: "slot", required: true, maxlength: 24, list: slotId, placeholder: "例如：宽槽",
      })),
      el("datalist", {id: massId}, bandOptions(selected, "mass").map(value => el("option", {value}))),
      el("datalist", {id: slotId}, bandOptions(selected, "slot").map(value => el("option", {value})))),
    field("撤回原因（可选）", el("input", {name: "reason", maxlength: 500, placeholder: "供货方撤回该档位对的实测依据"})),
    errorText(),
    notice,
    el("button", {type: "submit"}, "登记撤回"));

  submit(form, async values => {
    notice.textContent = "";
    const created = await api.withdrawBasis(selected.id, {
      mass: values.get("mass"),
      slot: values.get("slot"),
      reason: values.get("reason") || "",
    });
    form.reset();
    const latest = await api.withdrawals(selected.id);
    listHost.replaceChildren(withdrawalTable(latest));
    notice.textContent = `撤回登记 ${created.code || `#${created.id}`} 已生效，相关容量证明立即失效。`;
  });

  return section("实测依据撤回",
    el("p", {}, "登记后，所有查过该重量档/槽宽档组合的容量证明立即失效；查询结果为 0 也同样受影响。原始证明和签章会保留。"),
    listHost,
    canWithdraw ? form : empty("当前账号可查看撤回记录，登记撤回需要资料操作员权限。"));
}

export async function casesPage(config, user, route) {
  const cases = await api.cases();
  const selected = cases.find(item => item.id === route.id) ?? cases.at(-1);
  const withdrawals = selected ? await api.withdrawals(selected.id) : [];
  const operator = user.role === "operator";
  return el("div", {class: "page"},
    pageHeading(config.modules[1], `${config.unit} · ${config.fixture}`),
    section("资料目录", cases.length ? table(["编号", "名称", "说明", "操作"], cases.map(item =>
      [item.code, item.title, item.description,
        el("a", {href: `#cases/${item.id}`, "aria-current": item.id === selected?.id ? "true" : null}, "选用")]), "资料目录") :
      empty("这里还没有资料。")),
    el("div", {class: "split case-split"},
      section(selected ? selected.title : "等待选择资料", selected ?
        [el("p", {}, selected.description), operator ? queueForm(config, selected) : empty("当前账号可查看此资料。"),
          el("details", {}, el("summary", {}, "查看业务数据"), el("pre", {}, JSON.stringify(selected.payload, null, 2)))] :
        empty("先登记一条资料，再提交执行。")),
      operator ? section("登记新资料", registration(config, selected)) : null)),
    withdrawalPanel(selected, withdrawals, operator));
}
