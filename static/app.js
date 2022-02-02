const table_container = document.querySelector('#table-container'); //select the table container from the dom

// Updates the table with the data obtained from the HTTP request to the /update_list server endpoint
function updateTable() {
	fetch('http://172.16.40.31:5000/update_list', {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Accept: 'application/json',
		},
	})
		.then(function (response) {
			return response.json();
		})
		.then(function (data) {
			console.log('users: ', Object.values(data));

			let old_table = document.querySelector('#table-container').firstChild; //select the previous displayed table
			if (old_table) old_table.parentElement.removeChild(old_table); //if there is a displayed tables remove it from the DOM

			//create a new table from scratch with the data received from the server
			let table = document.createElement('table');
			table.classList.add('table');
			table.classList.add('table-dark');
			let header = document.createElement('tr');

			let ID = document.createElement('th');
			let Ticket_validated = document.createElement('th');
			let Face_mask = document.createElement('th');

			ID.innerHTML = 'ID';
			Ticket_validated.innerHTML = 'Ticket Validated';
			Face_mask.innerHTML = 'Face Mask';
			header.appendChild(ID);
			header.appendChild(Ticket_validated);
			header.appendChild(Face_mask);
			table.appendChild(header);

			for (let i = 0; i < Object.keys(data).length; i++) {
				let user = Object.values(data)[i];
				row = document.createElement('tr');
				idCell = document.createElement('td');
				ticketCell = document.createElement('td');
				maskCell = document.createElement('td');
				idCell.appendChild(document.createTextNode(parseInt(user.id).toString()));
				ticketCell.appendChild(document.createTextNode(user.ticket));
				maskCell.appendChild(document.createTextNode(user.face_mask));
				row.appendChild(idCell);
				row.appendChild(ticketCell);
				row.appendChild(maskCell);
				table.appendChild(row);
				table_container.appendChild(table);
			}
		});
}

//call the update_table (make a request to the server) every second
const vinterv = window.setInterval(function () {
	updateTable();
}, 1000);
