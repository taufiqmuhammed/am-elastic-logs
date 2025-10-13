document.getElementById("analyzeBtn").onclick = async function() {
  const question = document.getElementById("question").value.trim();
  const kValue    = parseInt(document.getElementById("k").value, 10) || 32;

  const resp = await fetch("/anomalies", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ query: question, k: kValue })
  });
  const data = await resp.json();

  document.getElementById("summary").textContent = data.summary || "No summary.";
  const list = document.getElementById("anomalies");
  list.innerHTML = "";
  data.confirmed_anomalies.forEach(a => {
    const li = document.createElement("li");
    li.textContent = `[i=${a.i}] ${a.reason} → ${a.next_action}`;
    list.appendChild(li);
  });
  document.getElementById("layman").textContent = data.layman_explanation;
};