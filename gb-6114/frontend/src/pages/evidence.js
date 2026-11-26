import { api } from "../api/workbench.js";
import { errorText, field } from "../components/common/fields.js";
import { empty, pageHeading, section } from "../components/common/panel.js";
import { resultTable } from "../components/common/table.js";
import { submit } from "../hooks/submit.js";
import { el } from "../utils/dom.js";
import { cell, download, time } from "../utils/format.js";

function reviewForm(id, saved) {
  const form = el("form", {id: "review-form"},
    field("复核意见", el("textarea", {name: "note", required: true, minlength: 3, maxlength: 500, rows: 3})),
    errorText(), el("button", {type: "submit"}, "签署复核"));
  submit(form, async values => saved(await api.submitReview(id, {note: values.get("note")})));
  return form;
}

function signature(review) {
  return el("div", {"data-testid": "reviewed", class: "signature"},
    el("strong", {}, `已签署 · ${review.actor}`), el("p", {}, review.note), el("time", {}, time(review.created_at)));
}

function pairText(pair) {
  return `${pair.mass} / ${pair.slot}`;
}

function invalidNotice(run) {
  if (run.valid !== false) return null;
  const pairs = run.withdrawn_pairs || [];
  return el("section", {
    class: "feature invalid-basis",
    "data-testid": "certificate-invalid",
    role: "alert",
  },
    el("h2", {}, "容量证明已失效"),
    el("p", {}, "以下档位对的实测依据已由供货方撤回。即使数据库实测为 0，只要本证明查过该组合即失效，不能签核或作为有效件交接。"),
    el("ul", {class: "withdrawn-pairs"}, pairs.map(pair => el("li", {}, pairText(pair)))),
    el("p", {}, "原始结果、摘要和已有签章均保留，可下载标注失效的回读件。"));
}

function withdrawalForm(run) {
  const pairs = run.queried_pairs || [];
  const massId = `evidence-mass-${run.id}`;
  const slotId = `evidence-slot-${run.id}`;
  const form = el("form", {id: `evidence-withdrawal-${run.id}`, class: "withdrawal-form"},
    el("div", {class: "form-grid"},
      field("重量档", el("input", {name: "mass", required: true, maxlength: 24, list: massId})),
      field("槽宽档", el("input", {name: "slot", required: true, maxlength: 24, list: slotId})),
      el("datalist", {id: massId}, [...new Set(pairs.map(pair => pair.mass))].map(value => el("option", {value}))),
      el("datalist", {id: slotId}, [...new Set(pairs.map(pair => pair.slot))].map(value => el("option", {value})))),
    field("原因（可选）", el("input", {name: "reason", maxlength: 500})),
    errorText(),
    el("button", {type: "submit"}, "登记撤回并刷新证明状态"));
  submit(form, async values => {
    await api.withdrawBasis(run.case_id, {
      mass: values.get("mass"),
      slot: values.get("slot"),
      reason: values.get("reason") || "",
    });
    window.location.reload();
  });
  return el("details", {}, el("summary", {}, "供货方撤回某对档位的实测依据"), form);
}

async function downloadEvidence(apiCall, filename, issue, button) {
  button.disabled = true;
  issue.textContent = "";
  try {
    await download(await apiCall, filename);
  } catch (error) {
    issue.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

export async function evidencePage(config, user, route) {
  const runs = (await api.runs()).filter(item => item.status === "done");
  const run = route.id ? await api.run(route.id) : runs[0];
  if (!run?.result) return el("div", {class: "page"},
    pageHeading(config.modules[3], null), empty("成功执行一个批次后可以查看、签核和下载证据。"),
    el("a", {href: "#runs"}, config.modules[2]));

  const review = await api.review(run.id);
  const issue = errorText();
  const invalid = run.valid === false;
  const button = el("button", {type: "button", onclick: event => {
    downloadEvidence(api.export(run.id), `evidence-${run.id}.json`, issue, event.currentTarget);
  }}, "导出证据 / 交接单");
  const readbackButton = el("button", {type: "button", class: "quiet", onclick: event => {
    downloadEvidence(api.evidenceBundle(run.id), `evidence-${run.id}-readback.json`, issue, event.currentTarget);
  }}, "下载标注回读件");
  const signing = el("div", {});
  if (invalid) {
    signing.append(
      el("p", {class: "invalid-signing", role: "alert", "data-testid": "sign-blocked"},
        "受撤回影响，此证明已失效，不能新增签核。"),
      review ? signature(review) : empty("失效前没有签章。"));
  } else if (review) {
    signing.append(signature(review));
  } else if (user.role === "reviewer") {
    const form = reviewForm(run.id, data => signing.replaceChildren(signature(data)));
    signing.append(form);
  } else {
    signing.append(empty("待复核员签署。"));
  }
  const options = el("select", {"aria-label": "选择已完成的批次", onchange: event => {
    location.hash = `evidence/${event.target.value}`;
  }}, runs.map(item => el("option", {value: item.id, selected: item.id === run.id},
    `#${item.id} ${item.case_title}${item.valid === false ? "（已失效）" : ""}`)));
  return el("div", {class: "page evidence"},
    pageHeading(config.modules[3], run.case_title, el("div", {class: "button-row"}, button, readbackButton)),
    issue, options,
    invalidNotice(run),
    el("section", {class: "feature evidence-summary"}, el("div", {}, el("h2", {}, "批次判定"), el("p", {}, run.result.summary)),
      el("details", {}, el("summary", {}, "证据摘要"), el("code", {}, run.digest))),
    el("dl", {class: "metrics"}, Object.entries(run.result.metrics).map(([label, value]) =>
      el("div", {}, el("dt", {}, label), el("dd", {}, cell(value))))),
    section("业务结果明细", run.result.rows.length ? resultTable(run.result.rows) : empty("此批次无明细。")),
    user.role === "operator" ? section("实测依据撤回", withdrawalForm(run)) : null,
    section("复核签署", signing));
}
