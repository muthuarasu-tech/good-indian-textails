(function () {
    "use strict";

    const form = document.getElementById("billing-form");
    if (!form) {
        return;
    }

    const itemsBody = document.getElementById("items-body");
    const rowTemplate = document.getElementById("item-row-template");
    const addButton = document.getElementById("add-item");
    const itemsInput = document.getElementById("items-json");
    const initialItemsElement = document.getElementById("initial-items");
    const alertBox = document.getElementById("form-alert");
    const alertText = document.getElementById("form-alert-text");
    const summarySubtotal = document.getElementById("summary-subtotal");
    const summaryDiscount = document.getElementById("summary-discount");
    const summaryTotal = document.getElementById("summary-total");
    const summaryCount = document.getElementById("summary-count");

    const currency = new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    function roundMoney(value) {
        return Math.round((value + Number.EPSILON) * 100) / 100;
    }

    function formatMoney(value) {
        return currency.format(Number.isFinite(value) ? value : 0);
    }

    function field(row, name) {
        return row.querySelector('[data-field="' + name + '"]');
    }

    function hideAlert() {
        alertBox.hidden = true;
        alertText.textContent = "";
    }

    function showAlert(message, target) {
        alertText.textContent = message;
        alertBox.hidden = false;
        alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
        if (target) {
            window.setTimeout(function () {
                target.focus();
            }, 230);
        }
    }

    function addRow(data) {
        const fragment = rowTemplate.content.cloneNode(true);
        const row = fragment.querySelector(".item-row");
        const values = data || {};

        if (values.item_name) {
            const select = field(row, "item_name");
            const optionExists = Array.from(select.options).some(function (option) {
                return option.value === values.item_name;
            });
            if (optionExists) {
                select.value = values.item_name;
            }
        }

        if (values.quantity !== undefined && values.quantity !== null) {
            field(row, "quantity").value = values.quantity;
        }
        if (values.cost !== undefined && values.cost !== null) {
            const cost = Number(values.cost);
            field(row, "cost").value = Number.isFinite(cost) && cost !== 0 ? cost : "";
        }
        if (values.discount !== undefined && values.discount !== null) {
            const discount = Number(values.discount);
            field(row, "discount").value = Number.isFinite(discount) && discount !== 0 ? discount : "";
        }

        itemsBody.appendChild(fragment);
        updateAll();
    }

    function updateRow(row) {
        const quantityInput = field(row, "quantity");
        const costInput = field(row, "cost");
        const discountInput = field(row, "discount");
        const quantity = Math.max(0, parseInt(quantityInput.value, 10) || 0);
        const cost = Math.max(0, parseFloat(costInput.value) || 0);
        const discount = Math.max(0, parseFloat(discountInput.value) || 0);
        const gross = roundMoney(quantity * cost);
        const lineTotal = Math.max(0, roundMoney(gross - discount));

        const discountTooHigh = discount > gross + 0.001;
        discountInput.classList.toggle("input-error", discountTooHigh);
        discountInput.setAttribute("aria-invalid", discountTooHigh ? "true" : "false");

        row.querySelector("[data-line-total]").textContent = formatMoney(lineTotal);
        row.dataset.lineTotal = String(lineTotal);
        row.dataset.gross = String(gross);
        row.dataset.discount = String(discount);
        row.dataset.quantity = String(quantity);
        row.dataset.cost = String(cost);
        row.dataset.discountTooHigh = discountTooHigh ? "true" : "false";
    }

    function updateAll() {
        const rows = Array.from(itemsBody.querySelectorAll(".item-row"));
        let subtotal = 0;
        let discountTotal = 0;

        rows.forEach(function (row, index) {
            row.querySelector(".row-number").textContent = index + 1;
            updateRow(row);
            subtotal += Number(row.dataset.gross || 0);
            discountTotal += Number(row.dataset.discount || 0);
        });

        subtotal = roundMoney(subtotal);
        discountTotal = roundMoney(discountTotal);
        const total = Math.max(0, roundMoney(subtotal - discountTotal));

        summarySubtotal.textContent = formatMoney(subtotal);
        summaryDiscount.textContent = (discountTotal > 0 ? "− " : "") + formatMoney(discountTotal);
        summaryTotal.textContent = formatMoney(total);
        summaryCount.textContent = rows.length + (rows.length === 1 ? " item" : " items");
    }

    function resetRow(row) {
        field(row, "item_name").selectedIndex = 0;
        field(row, "quantity").value = "1";
        field(row, "cost").value = "";
        field(row, "discount").value = "";
        updateAll();
        field(row, "cost").focus();
    }

    function removeRow(button) {
        const row = button.closest(".item-row");
        const rows = itemsBody.querySelectorAll(".item-row");
        if (rows.length === 1) {
            resetRow(row);
            return;
        }
        row.remove();
        updateAll();
    }

    function validateItems() {
        const rows = Array.from(itemsBody.querySelectorAll(".item-row"));
        if (!rows.length) {
            return { valid: false, message: "Add at least one item to the bill." };
        }

        for (let index = 0; index < rows.length; index += 1) {
            const row = rows[index];
            const itemName = field(row, "item_name").value;
            const quantity = parseInt(field(row, "quantity").value, 10);
            const costField = field(row, "cost");
            const cost = parseFloat(costField.value);
            const discountField = field(row, "discount");
            const discount = discountField.value.trim() === "" ? 0 : parseFloat(discountField.value);

            if (!itemName) {
                return { valid: false, message: "Choose an item for row " + (index + 1) + ".", target: field(row, "item_name") };
            }
            if (!Number.isFinite(quantity) || quantity < 1) {
                return { valid: false, message: "Quantity must be at least 1 for row " + (index + 1) + ".", target: field(row, "quantity") };
            }
            if (costField.value.trim() === "" || !Number.isFinite(cost) || cost < 0) {
                return { valid: false, message: "Enter a valid cost for row " + (index + 1) + ".", target: costField };
            }
            if (!Number.isFinite(discount) || discount < 0) {
                return { valid: false, message: "Enter a valid discount for row " + (index + 1) + ".", target: discountField };
            }
            if (discount > roundMoney(quantity * cost) + 0.001) {
                return { valid: false, message: "The discount for row " + (index + 1) + " cannot be more than its cost.", target: discountField };
            }
        }

        return { valid: true };
    }

    function collectItems() {
        return Array.from(itemsBody.querySelectorAll(".item-row")).map(function (row) {
            return {
                item_name: field(row, "item_name").value,
                quantity: parseInt(field(row, "quantity").value, 10) || 1,
                cost: roundMoney(parseFloat(field(row, "cost").value) || 0),
                discount: roundMoney(parseFloat(field(row, "discount").value) || 0),
            };
        });
    }

    addButton.addEventListener("click", function () {
        addRow();
        const rows = itemsBody.querySelectorAll(".item-row");
        const lastRow = rows[rows.length - 1];
        if (lastRow) {
            field(lastRow, "cost").focus();
            lastRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    });

    itemsBody.addEventListener("input", function (event) {
        if (event.target.matches("[data-field]")) {
            hideAlert();
            updateAll();
        }
    });

    itemsBody.addEventListener("change", function (event) {
        if (event.target.matches("[data-field]")) {
            updateAll();
        }
    });

    itemsBody.addEventListener("click", function (event) {
        const removeButton = event.target.closest(".remove-item");
        if (removeButton) {
            removeRow(removeButton);
        }
    });

    form.addEventListener("submit", function (event) {
        const validation = validateItems();

        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        if (!validation.valid) {
            event.preventDefault();
            showAlert(validation.message, validation.target);
            return;
        }

        updateAll();
        itemsInput.value = JSON.stringify(collectItems());
    });

    let initialItems = [];
    try {
        initialItems = JSON.parse(initialItemsElement.textContent || "[]");
    } catch (error) {
        initialItems = [];
    }

    if (Array.isArray(initialItems) && initialItems.length) {
        initialItems.forEach(function (item) {
            addRow(item);
        });
    } else {
        addRow();
    }
})();
