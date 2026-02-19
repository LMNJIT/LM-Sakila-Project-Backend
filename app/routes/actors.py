from flask import jsonify
from .. import app, mysql

# get top 5 actors - for landing page
@app.route('/api/actors/top', methods=['GET'])
def get_top_actors():
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
        select a.actor_id, a.first_name, a.last_name, COUNT(film_a.film_id) as film_count
        from actor a
        join film_actor film_a on a.actor_id = film_a.actor_id
        group by a.actor_id
        order by film_count desc
        limit 5
    """)
    
    top_actors = cursor.fetchall()
    cursor.close()
    
    return jsonify(top_actors), 200

# get actor info and their top films
@app.route('/api/actors/<int:actor_id>', methods=['GET'])
def get_actor_info(actor_id):
    cursor = mysql.connection.cursor()
    
    # get actor details
    cursor.execute("select actor_id, first_name, last_name, last_update from actor where actor_id = %s", (actor_id,))
    actor_data = cursor.fetchone()
    
    # get top 5 films for this actor
    cursor.execute("""
        select f.film_id, f.title, COUNT(r.rental_id) as rental_count
        from film f
        join film_actor film_a on f.film_id = film_a.film_id
        join inventory i on f.film_id = i.film_id
        join rental r on i.inventory_id = r.inventory_id
        where film_a.actor_id = %s
        group by f.film_id, f.title
        order by rental_count desc
        limit 5
    """, (actor_id,))
    films = cursor.fetchall()
    cursor.close()
    
    # add films to actor data
    actor_data['top_films'] = films
    
    return jsonify(actor_data), 200
