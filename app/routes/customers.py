from flask import jsonify, request
from .. import app, mysql


def _build_customer_search_clause(query_text, search_type):
    if query_text == '':
        return '', []

    if search_type == 'id':
        if not query_text.isdigit():
            return 'where 1 = 0', []
        return 'where customer_id = %s', [int(query_text)]

    if search_type == 'first_name':
        return 'where LOWER(first_name) LIKE LOWER(%s)', [f'%{query_text}%']

    if search_type == 'last_name':
        return 'where LOWER(last_name) LIKE LOWER(%s)', [f'%{query_text}%']

    return (
        'where CAST(customer_id AS CHAR) LIKE %s '
        'or LOWER(first_name) LIKE LOWER(%s) '
        'or LOWER(last_name) LIKE LOWER(%s)',
        [f'%{query_text}%', f'%{query_text}%', f'%{query_text}%']
    )

# get all customers
@app.route('/api/customers', methods=['GET'])
def get_customers():
    page_num = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 21, type=int)
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', '').strip().lower()

    if page_num < 1:
        page_num = 1
    if limit < 1:
        limit = 21

    offset = (page_num - 1) * limit

    where_clause, params = _build_customer_search_clause(q, search_type)
    
    cursor = mysql.connection.cursor()
    
    # get total
    cursor.execute("""
        select COUNT(*) as total from customer {}
    """.format(where_clause), params)
    count = cursor.fetchone()
    total = count['total']
    pages = (total + limit - 1) // limit
    
    # get customers
    customer_query = (
        f"select customer_id, first_name, last_name, email "
        f"from customer {where_clause} "
        f"order by customer_id asc "
        f"limit %s offset %s"
    )
    cursor.execute("""
        {}
    """.format(customer_query), params + [limit, offset])
    customer_list = cursor.fetchall()
    cursor.close()
    
    return jsonify({
        'customers': customer_list,
        'totalPages': pages
    }), 200

# search customers
@app.route('/api/customers/search', methods=['GET'])
def search_customers():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', '').strip().lower()
    
    if q == '':
        return jsonify([]), 200

    where_clause, params = _build_customer_search_clause(q, search_type)
    
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        select customer_id, first_name, last_name, email
        from customer {}
        order by customer_id asc
    """.format(where_clause), params)
    
    customer_results = cursor.fetchall()
    cursor.close()
    
    return jsonify(customer_results), 200

# get customer details with address
@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    cursor = mysql.connection.cursor()
    
    # get customer details with address info
    cursor.execute("""
        select c.customer_id, c.first_name, c.last_name, c.email, c.store_id, c.active, c.create_date, c.last_update,
        a.address, a.district, a.city_id, a.postal_code, a.phone
        from customer c
        join address a on c.address_id = a.address_id
        where c.customer_id = %s
    """, (customer_id,))
    
    customer = cursor.fetchone()
    cursor.close()
    
    # check if customer exists
    if customer == None:
        return jsonify({'error': 'Customer not found'}), 404
    
    return jsonify(customer), 200

# get customer rental history
@app.route('/api/customers/<int:customer_id>/rentals', methods=['GET'])
def get_customer_rentals(customer_id):
    cursor = mysql.connection.cursor()
    
    # get all rentals for this customer with film title and status
    cursor.execute("""
        select r.rental_id, r.rental_date, r.return_date, f.title, 
        case when r.return_date is null then 'out' else 'returned' end as status
        from rental r
        join inventory i on r.inventory_id = i.inventory_id
        join film f on i.film_id = f.film_id
        where r.customer_id = %s
        order by r.rental_date desc
    """, (customer_id,))
    
    rentals = cursor.fetchall()
    cursor.close()
    
    return jsonify(rentals), 200

# create a new customer
@app.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    
    # validate required fields
    required_fields = ['first_name', 'last_name', 'email', 'store_id', 'address', 'district', 'postal_code', 'phone']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # extract customer fields
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    store_id = data.get('store_id')
    active = data.get('active', 1)
    
    # extract address fields
    address = data.get('address', '').strip()
    district = data.get('district', '').strip()
    postal_code = data.get('postal_code', '').strip()
    phone = data.get('phone', '').strip()
    city_id = data.get('city_id', 1)
    
    # validate customer fields
    if not first_name or len(first_name) > 45:
        return jsonify({'error': 'Invalid first_name (1-45 characters)'}), 400
    if not last_name or len(last_name) > 45:
        return jsonify({'error': 'Invalid last_name (1-45 characters)'}), 400
    if not email or len(email) > 50:
        return jsonify({'error': 'Invalid email (1-50 characters)'}), 400
    if not isinstance(store_id, int) or store_id < 1:
        return jsonify({'error': 'Invalid store_id (must be positive integer)'}), 400
    if not isinstance(active, int) or active not in [0, 1]:
        return jsonify({'error': 'Invalid active (must be 0 or 1)'}), 400
    
    # validate address fields
    if not address:
        return jsonify({'error': 'Invalid address'}), 400
    if not district:
        return jsonify({'error': 'Invalid district'}), 400
    if not postal_code:
        return jsonify({'error': 'Invalid postal_code'}), 400
    if not phone:
        return jsonify({'error': 'Invalid phone'}), 400
    if not isinstance(city_id, int) or city_id < 1:
        return jsonify({'error': 'Invalid city_id (must be positive integer)'}), 400
    
    cursor = mysql.connection.cursor()
    
    try:
        # insert new address first
        cursor.execute("""
            insert into address (address, address2, district, city_id, postal_code, phone, location, last_update)
            values (%s, %s, %s, %s, %s, %s, point(0, 0), now())
        """, (address, data.get('address2', ''), district, city_id, postal_code, phone))
        
        mysql.connection.commit()
        
        # get the newly created address_id using lastrowid
        address_id = cursor.lastrowid
        
        # insert new customer with the address_id
        cursor.execute("""
            insert into customer (store_id, first_name, last_name, email, address_id, active, create_date, last_update)
            values (%s, %s, %s, %s, %s, %s, now(), now())
        """, (store_id, first_name, last_name, email, address_id, active))
        
        mysql.connection.commit()
        
        # get the newly created customer
        cursor.execute("""
            select customer_id, first_name, last_name, email, store_id, active, create_date, last_update
            from customer
            where customer_id = %s
        """, (cursor.lastrowid,))
        
        new_customer = cursor.fetchone()
        cursor.close()
        
        return jsonify(new_customer), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 400

# update customer details
@app.route('/api/customers/<int:customer_id>', methods=['PATCH'])
def update_customer(customer_id):
    data = request.get_json()
    
    cursor = mysql.connection.cursor()
    
    # check if customer exists and get address_id
    cursor.execute("""
        select customer_id, address_id from customer where customer_id = %s
    """, (customer_id,))
    
    customer = cursor.fetchone()
    if customer == None:
        cursor.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    address_id = customer['address_id']
    
    # extract editable customer fields
    first_name = data.get('first_name', '').strip() if 'first_name' in data else None
    last_name = data.get('last_name', '').strip() if 'last_name' in data else None
    email = data.get('email', '').strip() if 'email' in data else None
    active = data.get('active') if 'active' in data else None
    
    # extract editable address fields
    address = data.get('address', '').strip() if 'address' in data else None
    address2 = data.get('address2', '').strip() if 'address2' in data else None
    district = data.get('district', '').strip() if 'district' in data else None
    postal_code = data.get('postal_code', '').strip() if 'postal_code' in data else None
    phone = data.get('phone', '').strip() if 'phone' in data else None
    city_id = data.get('city_id') if 'city_id' in data else None
    
    # validate customer fields if provided
    if first_name is not None and (not first_name or len(first_name) > 45):
        cursor.close()
        return jsonify({'error': 'Invalid first_name (1-45 characters)'}), 400
    if last_name is not None and (not last_name or len(last_name) > 45):
        cursor.close()
        return jsonify({'error': 'Invalid last_name (1-45 characters)'}), 400
    if email is not None and (not email or len(email) > 50):
        cursor.close()
        return jsonify({'error': 'Invalid email (1-50 characters)'}), 400
    if active is not None and (not isinstance(active, int) or active not in [0, 1]):
        cursor.close()
        return jsonify({'error': 'Invalid active (must be 0 or 1)'}), 400
    
    # validate address fields if provided
    if address is not None and not address:
        cursor.close()
        return jsonify({'error': 'Invalid address'}), 400
    if district is not None and not district:
        cursor.close()
        return jsonify({'error': 'Invalid district'}), 400
    if postal_code is not None and not postal_code:
        cursor.close()
        return jsonify({'error': 'Invalid postal_code'}), 400
    if phone is not None and not phone:
        cursor.close()
        return jsonify({'error': 'Invalid phone'}), 400
    if city_id is not None and (not isinstance(city_id, int) or city_id < 1):
        cursor.close()
        return jsonify({'error': 'Invalid city_id (must be positive integer)'}), 400
    
    try:
        # update address fields if any provided
        address_update_fields = []
        address_update_params = []
        
        if address is not None:
            address_update_fields.append('address = %s')
            address_update_params.append(address)
        if address2 is not None:
            address_update_fields.append('address2 = %s')
            address_update_params.append(address2)
        if district is not None:
            address_update_fields.append('district = %s')
            address_update_params.append(district)
        if postal_code is not None:
            address_update_fields.append('postal_code = %s')
            address_update_params.append(postal_code)
        if phone is not None:
            address_update_fields.append('phone = %s')
            address_update_params.append(phone)
        if city_id is not None:
            address_update_fields.append('city_id = %s')
            address_update_params.append(city_id)
        
        if address_update_fields:
            address_update_fields.append('last_update = now()')
            address_update_params.append(address_id)
            
            cursor.execute("""
                update address set {} where address_id = %s
            """.format(', '.join(address_update_fields)), address_update_params)
        
        # update customer fields if any provided
        customer_update_fields = []
        customer_update_params = []
        
        if first_name is not None:
            customer_update_fields.append('first_name = %s')
            customer_update_params.append(first_name)
        if last_name is not None:
            customer_update_fields.append('last_name = %s')
            customer_update_params.append(last_name)
        if email is not None:
            customer_update_fields.append('email = %s')
            customer_update_params.append(email)
        if active is not None:
            customer_update_fields.append('active = %s')
            customer_update_params.append(active)
        
        if customer_update_fields:
            customer_update_fields.append('last_update = now()')
            customer_update_params.append(customer_id)
            
            cursor.execute("""
                update customer set {} where customer_id = %s
            """.format(', '.join(customer_update_fields)), customer_update_params)
        
        # check if any updates were made
        if not address_update_fields and not customer_update_fields:
            cursor.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        mysql.connection.commit()
        
        # fetch updated customer with address info
        cursor.execute("""
            select c.customer_id, c.first_name, c.last_name, c.email, c.store_id, c.active, c.create_date, c.last_update,
                   a.address, a.district, a.city_id, a.postal_code, a.phone
            from customer c
            join address a on c.address_id = a.address_id
            where c.customer_id = %s
        """, (customer_id,))
        
        updated_customer = cursor.fetchone()
        cursor.close()
        
        return jsonify(updated_customer), 200
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 400

# delete customer
@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    cursor = mysql.connection.cursor()
    
    # check if customer exists
    cursor.execute("""
        select customer_id, first_name, last_name from customer where customer_id = %s
    """, (customer_id,))
    
    customer = cursor.fetchone()
    if customer == None:
        cursor.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    # check if customer has active rentals
    cursor.execute("""
        select COUNT(*) as active_rentals
        from rental
        where customer_id = %s and return_date is null
    """, (customer_id,))
    
    rental_check = cursor.fetchone()
    active_rentals = rental_check['active_rentals']
    
    if active_rentals > 0:
        cursor.close()
        return jsonify({'error': f'Cannot delete customer with {active_rentals} active rental(s). Customer must return all rented items first.'}), 400
    
    try:
        # delete in order of foreign key dependencies
        # 1. delete from payment (references customer_id)
        cursor.execute("""
            delete from payment where customer_id = %s
        """, (customer_id,))
        
        # 2. delete from rental (references customer_id)
        cursor.execute("""
            delete from rental where customer_id = %s
        """, (customer_id,))
        
        # 3. delete from customer
        cursor.execute("""
            delete from customer where customer_id = %s
        """, (customer_id,))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': f'Customer {customer["first_name"]} {customer["last_name"]} has been permanently deleted'}), 200
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 400
