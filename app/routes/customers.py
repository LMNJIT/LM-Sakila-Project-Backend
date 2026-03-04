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
