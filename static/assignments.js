function editable(assignId) {
    let nameElem = document.getElementById(assignId + "_name")
    let dueElem = document.getElementById(assignId + "_due")
    let editBtn = document.getElementById(assignId + "_edit")

    let month, day, year, hour, minute, second, ampm
    let timedue = dueElem.innerText.split(" ")
    let pt1 = timedue[0].split("/")
    let pt2 = timedue[1].split(":")
    month = pt1[0]
    day = pt1[1]
    year = pt1[2]
    hour = pt2[0]
    minute = pt2[1]
    second = pt2[2]
    ampm = timedue[2]
    if (ampm == "PM") {
        hour = parseInt(hour) + 12
    }
    nameElem.innerHTML = `<input class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" name="name" value="${nameElem.innerText}"/>`
    dueElem.innerHTML = `<input type="datetime-local" value="${year}-${month}-${day}T${hour}:${minute}:${second}" />`
    editBtn.innerHTML = `<polyline points="20 6 9 17 4 12"></polyline>`
    editBtn.setAttribute("onclick", `makeFormAndSave("${assignId}")`)
}

function makeFormAndSave(assignId) {
    let courseId = document.querySelector("meta[name='classId']").getAttribute("content")

    let nameElem = document.getElementById(assignId + "_name")
    let dueElem = document.getElementById(assignId + "_due")
    let editBtn = document.getElementById(assignId + "_edit")

    let name = nameElem.querySelector("input").value
    let due = dueElem.querySelector("input").value

    let form = document.createElement("form")
    form.setAttribute("method", "POST")
    form.setAttribute("action", `/class/${courseId}/assignment/${assignId}/edit`)

    let nameInput = document.createElement("input")
    nameInput.setAttribute("type", "hidden")
    nameInput.setAttribute("name", "name")
    nameInput.setAttribute("value", name)

    let dueInput = document.createElement("input")
    dueInput.setAttribute("type", "hidden")
    dueInput.setAttribute("name", "due")
    dueInput.setAttribute("value", due)

    form.appendChild(nameInput)
    form.appendChild(dueInput)

    document.body.appendChild(form)
    form.submit()
}

function change_complete_status(assignId) {
    let courseId = document.querySelector("meta[name='classId']").getAttribute("content")
    let completeBtn = document.getElementById(assignId + "_complete")
    let form = document.createElement("form")
    form.setAttribute("method", "POST")
    if (completeBtn.checked) {
    form.setAttribute("action", `/class/${courseId}/assignment/${assignId}/complete`)
    } else {
    form.setAttribute("action", `/class/${courseId}/assignment/${assignId}/uncomplete`)
    }
    document.body.appendChild(form)
    form.submit()
}

window.editable = editable
window.makeFormAndSave = makeFormAndSave
window.change_complete_status = change_complete_status