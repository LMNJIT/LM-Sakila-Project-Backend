from flask import jsonify, request
from .. import app, mysql

# get all customers
@app.route('/api/customers', methods=['GET'])
def get_customers():
    page_num = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 21, type=int)
    offset = (page_num - 1) * limit
    
    cursor = mysql.connection.cursor()
    
    # get total
    cursor.execute("select COUNT(*) as total from customer")
    count = cursor.fetchone()
    total = count['total']
    pages = (total + limit - 1) // limit
    
    # get customers
    cursor.execute("select customer_id, first_name, last_name, email from customer limit %s offset %s", (limit, offset))
    customer_list = cursor.fetchall()
    cursor.close()
    
    return jsonify({
        'customers': customer_list,
        'totalPages': pages
    }), 200

# search customers
@app.route('/api/customers/search', methods=['GET'])
def search_customers():
    q = request.args.get('q', '')
    
    # print(f"Searching for: {q}")  # debugging
    
    cursor = mysql.connection.cursor()
    
    # search in customer_id, first_name, and last_name
    cursor.execute("""
        select customer_id, first_name, last_name, email from customer
        where customer_id like %s or first_name like %s or last_name like %s
    """, (f'%{q}%', f'%{q}%', f'%{q}%'))
    
    customer_results = cursor.fetchall()
    cursor.close()
    
    return jsonify(customer_results), 200
