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
