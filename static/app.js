const table_container = document.querySelector('#table-container');

const sample_data = {
	user1: { id: 1, ticket_validated: true, face_mask: true },
	user2: { id: 2, ticket_validated: false, face_mask: true },
	user3: { id: 3, ticket_validated: false, face_mask: false },
};


function updateTable() {
	
	fetch('http://172.16.40.31:5000/update_list', {
		method : 'GET',
		headers : {
		  'Content-Type': 'application/json',
		  'Accept': 'application/json'
		 }})
	.then(function(response) {return response.json();})
	.then(function(data) {
			// console.log(data);
			console.log('users: ',Object.values(data))
						
			let old_table = document.querySelector('#table-container').firstChild;
			if (old_table) old_table.parentElement.removeChild(old_table);

			let table = document.createElement('table');
			table.classList.add("table")
			table.classList.add("table-dark")
			let header = document.createElement('tr');

			let ID = document.createElement("th");
			let Ticket_validated = document.createElement("th");
			let Face_mask = document.createElement("th");
			
			ID.innerHTML='ID';
			Ticket_validated.innerHTML='Ticket Validated';
			Face_mask.innerHTML='Face Mask';

			header.appendChild(ID);
			header.appendChild(Ticket_validated);
			header.appendChild(Face_mask);

			table.appendChild(header);

			for (let i = 0; i < Object.keys(data).length; i++) {
			let user = Object.values(data)[i];

			row = document.createElement('tr');
			idCell = document.createElement('td')
			ticketCell = document.createElement('td')
			maskCell = document.createElement('td')

			idCell.appendChild(document.createTextNode(parseInt(user.id).toString()))
			ticketCell.appendChild(document.createTextNode(user.ticket))
			maskCell.appendChild(document.createTextNode(user.face_mask))

			row.appendChild(idCell)
			row.appendChild(ticketCell)
			row.appendChild(maskCell)

			table.appendChild(row)
			

			table_container.appendChild(table);

			// if (!ids_displayed.includes(user.id)){
			// const row = table.insertRow(i + 1);
			// let id_cell = row.insertCell(0);
			// let ticket_validated_cell = row.insertCell(1);
			// let face_mask_cell = row.insertCell(2);

			// id_cell.innerHTML = user.id.toString();
			// ticket_validated_cell.innerHTML = user.ticket;
			// face_mask_cell.innerHTML = user.face_mask;
			// }
		}});

	// console.log(data);

}

const vinterv = window.setInterval(function() {updateTable()}, 1000);
