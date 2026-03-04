from flask import jsonify, request
from .. import app, mysql

# rent a film to a customer
@app.route('/api/rentals', methods=['POST'])
def create_rental():
    data = request.get_json()
    
    # validate required fields
    required_fields = ['customer_id', 'film_id', 'staff_id']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    customer_id = data.get('customer_id')
    film_id = data.get('film_id')
    staff_id = data.get('staff_id')
    
    # validate types
    if not isinstance(customer_id, int) or customer_id < 1:
        return jsonify({'error': 'Invalid customer_id'}), 400
    if not isinstance(film_id, int) or film_id < 1:
        return jsonify({'error': 'Invalid film_id'}), 400
    if not isinstance(staff_id, int) or staff_id < 1:
        return jsonify({'error': 'Invalid staff_id'}), 400

    cursor = mysql.connection.cursor()
    
    try:
        # check if customer exists and is active
        cursor.execute("""
            select customer_id, active from customer where customer_id = %s
        """, (customer_id,))
        
        customer = cursor.fetchone()
        if customer == None:
            cursor.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        if customer['active'] == 0:
            cursor.close()
            return jsonify({'error': 'Customer is inactive and cannot rent films'}), 400
        
        # check if film exists
        cursor.execute("""
            select film_id, title from film where film_id = %s
        """, (film_id,))
        
        film = cursor.fetchone()
        if film == None:
            cursor.close()
            return jsonify({'error': 'Film not found'}), 404
        
        # find available inventory (not currently rented out)
        cursor.execute("""
            select i.inventory_id, i.store_id
            from inventory i
            where i.film_id = %s
            and i.inventory_id NOT IN (
            select r.inventory_id from rental r where r.return_date is null
            )
            limit 1
        """, (film_id,))
        
        inventory = cursor.fetchone()
        if inventory == None:
            cursor.close()
            return jsonify({'error': f'No available copies of "{film["title"]}" to rent'}), 400
        
        inventory_id = inventory['inventory_id']
        
        # create rental record
        cursor.execute("""
            insert into rental (rental_date, inventory_id, customer_id, return_date, staff_id, last_update)
            values (now(), %s, %s, null, %s, now())
        """, (inventory_id, customer_id, staff_id))
        
        mysql.connection.commit()
        
        # fetch created rental
        cursor.execute("""
            select r.rental_id, r.rental_date, r.inventory_id, r.customer_id, r.return_date, r.staff_id, r.last_update,
            f.title, c.first_name, c.last_name
            from rental r
            join inventory i on r.inventory_id = i.inventory_id
            join film f on i.film_id = f.film_id
            join customer c on r.customer_id = c.customer_id
            where r.rental_id = last_insert_id()
        """)
        
        new_rental = cursor.fetchone()
        cursor.close()
        
        return jsonify(new_rental), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 400
