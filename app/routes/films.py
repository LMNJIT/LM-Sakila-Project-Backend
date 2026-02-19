from flask import jsonify, request
from .. import app, mysql

# get all films
@app.route('/api/films', methods=['GET'])
def get_films():
    # get page number from query params
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 21, type=int)
    offset = (page - 1) * limit
    
    # print(f"Page: {page}, Limit: {limit}")  # debugging
    
    cursor = mysql.connection.cursor()
    
    # get total count
    cursor.execute("select COUNT(f.film_id) as total from film f")
    result = cursor.fetchone()
    total_count = result['total']
    total_pages = (total_count + limit - 1) // limit
    
    # query to get films with category
    query = """
        select f.*, c.name as category
        from film f
        join film_category film_c on f.film_id = film_c.film_id
        join category c on film_c.category_id = c.category_id
        limit %s offset %s
    """
    cursor.execute(query, (limit, offset))
    films = cursor.fetchall()
    cursor.close()
    
    response = {
        'films': films,
        'totalPages': total_pages
    }
    return jsonify(response), 200

# get single film details
@app.route('/api/films/<int:film_id>', methods=['GET'])
def get_film_details(film_id):
    cursor = mysql.connection.cursor()
    
    # SQL query to get film info
    cursor.execute("""
        select f.*, c.name as category
        from film f
        join film_category film_c on f.film_id = film_c.film_id
        join category c on film_c.category_id = c.category_id
        where f.film_id = %s
    """, (film_id,))
    
    film = cursor.fetchone()
    cursor.close()
    
    # check if film exists
    if film == None:
        return jsonify({'error': 'Film not found'}), 404
    
    return jsonify(film), 200

# search films
@app.route('/api/films/search', methods=['GET'])
def search_films():
    search_query = request.args.get('q', '').strip()
    search_type = request.args.get('type', '').strip().lower()
    
    # print(f"Search query: {search_query}, type: {search_type}")  # for debugging
    
    if search_query == "":
        return jsonify([]), 200
    
    cursor = mysql.connection.cursor()
    results = []
    
    # search by category
    if search_type == 'category':
        cursor.execute("""
            select f.*, c.name as category
            from category c
            join film_category film_c on c.category_id = film_c.category_id
            join film f on film_c.film_id = f.film_id
            where LOWER(c.name) LIKE LOWER(%s)
        """, (f'%{search_query}%',))
        results = cursor.fetchall()
    
    # search by actor name
    elif search_type == 'actor':
        # split name into first and last
        name_parts = search_query.split()
        if len(name_parts) == 2:
            fname = name_parts[0]
            lname = name_parts[1]
            
            # find actor first
            cursor.execute("""
                select actor_id from actor
                where LOWER(first_name) = LOWER(%s) and LOWER(last_name) = LOWER(%s)
            """, (fname, lname))
            actor_result = cursor.fetchone()
            
            if actor_result:
                actor_id = actor_result['actor_id']
                # get films for this actor
                cursor.execute("""
                    select f.*, c.name as category
                    from film f
                    join film_actor film_a on f.film_id = film_a.film_id
                    join film_category film_c on f.film_id = film_c.film_id
                    join category c on film_c.category_id = c.category_id
                    where film_a.actor_id = %s
                """, (actor_id,))
                results = cursor.fetchall()
    
    # search by title
    elif search_type == 'title':
        cursor.execute("""
            select f.*, c.name as category
            from film f
            join film_category film_c on f.film_id = film_c.film_id
            join category c on film_c.category_id = c.category_id
            where LOWER(f.title) LIKE LOWER(%s)
        """, (f'%{search_query}%',))
        results = cursor.fetchall()
    
    # default search 
    else:
        cursor.execute("""
            select f.*, c.name as category
            from film f
            join film_category film_c on f.film_id = film_c.film_id
            join category c on film_c.category_id = c.category_id
            where f.title like %s or f.description like %s or c.name like %s
        """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        results = cursor.fetchall()
    
    cursor.close()
    return jsonify(results), 200

# top 5 rented films
@app.route('/api/films/top-rented', methods=['GET'])
def get_top_rented():
    cursor = mysql.connection.cursor()
    
    # query to get top rented films
    query = """
        select f.film_id, f.title, c.name as category, COUNT(r.rental_id) as rental_count
        from film f
        join inventory i on f.film_id = i.film_id
        join rental r on i.inventory_id = r.inventory_id
        join film_category film_c on f.film_id = film_c.film_id
        join category c on film_c.category_id = c.category_id
        group by f.film_id, f.title, c.name
        order by rental_count desc
        limit 5
    """
    cursor.execute(query)
    top_films = cursor.fetchall()
    cursor.close()
    
    return jsonify(top_films), 200
