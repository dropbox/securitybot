/**
 * Oh javascript, how I haven't missed you.
 * @author = Alex Bertsch
 * @email = abertsch@dropbox.com
 *
 * This is the main JavaScript source file for the Securitybot front end.
 * This should be placed _last_ in the HTML file.
 * It relies on jQuery and DataTables.
 */

function removeEmpty(obj) {
  for (let key in obj) {
    if (obj[key] === "") {
      delete obj[key];
    }
  }
}

function updateTable(id, arr) {
  let table = $(id).dataTable();
  table.fnClearTable();
  if (arr.length > 0) {
    table.fnAddData(arr);
  }
}

function setVisible(id) {
  document.getElementById(id).style.visibility = "visible";
}

function setHidden(id) {
  document.getElementById(id).style.visibility = "hidden";
}

function hideAlert() {
  document.getElementById("globalAlert").style.display = "none";
}

function showAlert() {
  document.getElementById("globalAlert").style.display = "block";
}

function presentAlert(style, message) {
  let alert = document.getElementById("globalAlert");
  showAlert();
  alert.innerHTML = message;
  alert.className = "alert " + style;
  setTimeout(hideAlert, 5000);
}

 /**
  * Submit actions for the alerts form.
  * Parses form data and sends a GET request to update the table.
  */
function submitAlerts(form) {
  // Read data from form
  // There's absolutely a better way to do this.
  let data = {};
  data["limit"] = form.alertsLimit.value;
  data["titles"] = form.alertsTitles.value;
  data["ldap"] = form.alertsLdap.value;

  data["status"] = form.querySelector("input[name=\"alertsStatus\"]:checked").value;
  data["performed"] = form.querySelector("input[name=\"alertsPerformed\"]:checked").value;
  data["authenticated"] = form.querySelector("input[name=\"alertsAuthenticated\"]:checked").value;
  // Remove "any"s
  for (let key of ["status", "performed", "authenticated"]) {
    if (data[key] === "any") {
      delete data[key];
    }
  }

  data["after"] = form.alertsAfter.value;
  data["before"] = form.alertsBefore.value;
  // Parse dates
  for (let key of ["after", "before"]) {
    if (data[key]) {
      data[key] = Date.parse(data[key]) / 1000;
    }
  }

  removeEmpty(data);

  // Use jQuery for a GET request because I'm so sorry
  setVisible("alertsLoading");
  $.get("api/query", data, updateAlerts);

  // Prevent page from updating
  return false;
}

let statuses = {
  0: "New",
  1: "In progress",
  2: "Complete",
};

/**
 * Actually update the alerts form using JSON data from an API request.
 */
function updateAlerts(data) {
  setHidden("alertsLoading");
  if (!data["ok"]) {
    presentAlert("alert-danger", "<strong>Error:</strong> " + data["error"]);
    return;
  }

  // Convert various values
  for (let alert of data["content"]["alerts"]) {
    // Timestamp => ISO string
    alert["event_time"] = new Date(parseInt(alert["event_time"]) * 1000).toISOString();

    // Status => readable string
    alert["status"] = statuses[alert["status"]];

    // Cast integers to booleans
    alert["performed"] = Boolean(alert["performed"]);
    alert["authenticated"] = Boolean(alert["authenticated"]);
  }

  updateTable("#alertsTable", data["content"]["alerts"]);
}

/**
 * Form submission handler for querying ignored alerts.
 */
function submitIgnored(form) {
  let data = {};
  data["limit"] = form.ignoredLimit.value;
  data["ldap"] = form.ignoredLdap.value;

  removeEmpty(data);

  setVisible("ignoredLoading");
  $.get("api/ignored", data, updateIgnored);

  return false;
}

/**
 * Updates the ignored table with a JSON response.
 */
function updateIgnored(data) {
  setHidden("ignoredLoading");
  if (!data["ok"]) {
    presentAlert("alert-danger", "<strong>Error:</strong> " + data["error"]);
    return;
  }

  // Convert dates to something readable
  for (let alert of data["content"]["ignored"]) {
    alert["until"] = new Date(parseInt(alert["until"]) * 1000).toISOString();
  }

  updateTable("#ignoredTable", data["content"]["ignored"]);
}

/**
 * Form submission handler for the blacklist.
 */
function submitBlacklist(form) {
  let data = {};
  data["limit"] = form.blacklistLimit.value;

  removeEmpty(data);

  setVisible("blacklistLoading");
  $.get("api/blacklist", data, updateBlacklist);

  return false;
}

/**
 * Updates the blacklist table with JSON from an API response.
 */
function updateBlacklist(data) {
  setHidden("blacklistLoading");
  if (!data["ok"]) {
    presentAlert("alert-danger", "<strong>Error:</strong> " + data["error"]);
    return;
  }

  updateTable("#blacklistTable", data["content"]["blacklist"]);
}

/**
 * Easter egg to bother use if they toggle the one column in the table.
 */
function didYouReallyToggleThat(item) {
  let box = $(item);
  if (!box.prop("checked")) {
    alert("Really?");
  }
}

/**
 * Submission call for custom alert form.
 */
function submitCustom(form) {
  let data = {};
  data["title"] = form.customTitle.value;
  data["ldap"] = form.customLdap.value;
  data["description"] = form.customDescription.value;
  data["reason"] = form.customReason.value;

  // Check for empty title or ldap
  let hasError = false;
  if (data["title"] === "") {
    form.customTitle.parentElement.parentElement.classList.add("has-error");
    hasError = true;
  } else {
    form.customTitle.parentElement.parentElement.classList.remove("has-error");
  }
  if (data["ldap"] === "") {
    form.customLdap.parentElement.parentElement.classList.add("has-error");
    hasError = true;
  } else {
    form.customLdap.parentElement.parentElement.classList.remove("has-error");
  }

  if (hasError) {
    presentAlert("alert-danger", "Please fill in the fields highlighted in red.");
  } else {
    setVisible("customLoading");
    $.post("api/create", data, validateCustom);
  }

  return false;
}

/**
 * Validate custom alert creation.
 */
function validateCustom(data) {
  setHidden("customLoading");
  if (data["ok"]) {
    presentAlert("alert-success", "<strong>Success:</strong> Alert created!");
  } else {
    presentAlert("alert-danger", "<strong>Error creating alert:</strong> " + data["error"]);
  }
}

// Page initialization
$(document).ready(function() {
  // Initialize DataTables
  let alertsTable = $("#alertsTable").DataTable({
    columns: [
      { name: "title", data: "title", title: "Title" },
      { name: "username", data: "ldap", title: "Username" },
      { name: "description", data: "description", title: "Description" },
      { name: "reason", data: "reason", title: "Reason" },
      { name: "performed", data: "performed", title: "Performed" },
      { name: "authenticated", data: "authenticated", title: "Authenticated" },
      { name: "url", data: "url", title: "URL" },
      { name: "status", data: "status", title: "Status" },
      { name: "event_time", data: "event_time", title: "Event time" },
      { name: "hash", data: "hash", title: "Hash", visible: false }
    ],
    colReorder: true,
  });

  let ignoredTable = $("#ignoredTable").DataTable({
    columns: [
      { name: "title", data: "title", title: "Title" },
      { name: "username", data: "ldap", title: "Username" },
      { name: "until", data: "until", title: "Ignored until" },
      { name: "reason", data: "reason", title: "Reason" },
    ],
    colReorder: true,
  });

  let blacklistTable = $("#blacklistTable").DataTable({
    columns: [
      { name: "username", data: "ldap", title: "Username" },
    ],
    colReorder: true,
  });

  let tables = {
    alerts: alertsTable,
    ignored: ignoredTable,
    blacklist: blacklistTable,
  };

  // Set up visibility toggles
  $(".toggle-vis").on("click", function () {
    let box = $(this);

    // Get the column API object
    let column = tables[box.attr("parent")].column(box.attr("name") + ":name");

    // Toggle column visibility
    column.visible(!column.visible());
  });
});
