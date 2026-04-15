from flask import Blueprint, request, jsonify, url_for
from app import db
from app.models import Partido, Usuario, Prediccion
from datetime import datetime
import math

# Crear blueprints
partidos_bp = Blueprint('partidos', __name__)
usuarios_bp = Blueprint('usuarios', __name__)
ranking_bp = Blueprint('ranking', __name__)

# Helper para generar enlaces HATEOAS
def generar_links(endpoint, total, limit, offset, **filtros):
    """Genera los enlaces de paginación HATEOAS"""
    links = {}
    
    # First
    links['_first'] = {
        'href': url_for(endpoint, _limit=limit, _offset=0, **filtros, _external=True)
    }
    
    # Last
    last_offset = math.ceil(total / limit) * limit - limit if total > 0 else 0
    links['_last'] = {
        'href': url_for(endpoint, _limit=limit, _offset=last_offset, **filtros, _external=True)
    }
    
    # Prev
    if offset - limit >= 0:
        links['_prev'] = {
            'href': url_for(endpoint, _limit=limit, _offset=offset - limit, **filtros, _external=True)
        }
    else:
        links['_prev'] = None
    
    # Next
    if offset + limit < total:
        links['_next'] = {
            'href': url_for(endpoint, _limit=limit, _offset=offset + limit, **filtros, _external=True)
        }
    else:
        links['_next'] = None
    
    return links

# ==================== RUTAS DE PARTIDOS ====================

@partidos_bp.route('/partidos', methods=['GET'])
def listar_partidos():
    """GET /partidos - Listar partidos con filtros y paginación"""
    # Obtener parámetros
    equipo = request.args.get('equipo')
    fecha_str = request.args.get('fecha')
    fase = request.args.get('fase')
    limit = int(request.args.get('_limit', 10))
    offset = int(request.args.get('_offset', 0))
    
    # Construir query
    query = Partido.query
    
    if equipo:
        query = query.filter(
            (Partido.equipo_local == equipo) | 
            (Partido.equipo_visitante == equipo)
        )
    
    if fecha_str:
        try:
            fecha = datetime.fromisoformat(fecha_str)
            query = query.filter(db.func.date(Partido.fecha) == fecha.date())
        except:
            pass
    
    if fase:
        query = query.filter(Partido.fase == fase)
    
    # Paginación
    total = query.count()
    partidos = query.offset(offset).limit(limit).all()
    
    # Generar respuesta
    return jsonify({
        'partidos': [p.to_resumen() for p in partidos],
        '_links': generar_links('partidos.listar_partidos', total, limit, offset,
                               equipo=equipo, fecha=fecha_str, fase=fase)
    }), 200

@partidos_bp.route('/partidos', methods=['POST'])
def crear_partido():
    """POST /partidos - Crear nuevo partido"""
    data = request.get_json()
    
    # Validaciones básicas
    required_fields = ['equipo_local', 'equipo_visitante', 'fecha', 'fase']
    for field in required_fields:
        if field not in data:
            return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': f'Campo {field} requerido'}]}), 400
    
    try:
        fecha = datetime.fromisoformat(data['fecha'].replace('Z', '+00:00'))
    except:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'Formato de fecha inválido'}]}), 400
    
    partido = Partido(
        equipo_local=data['equipo_local'],
        equipo_visitante=data['equipo_visitante'],
        fecha=fecha,
        fase=data['fase']
    )
    
    db.session.add(partido)
    db.session.commit()
    
    return jsonify(partido.to_dict()), 201

@partidos_bp.route('/partidos/<int:id>', methods=['GET'])
def obtener_partido(id):
    """GET /partidos/{id} - Obtener partido por ID"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    return jsonify(partido.to_dict()), 200

@partidos_bp.route('/partidos/<int:id>', methods=['PUT'])
def reemplazar_partido(id):
    """PUT /partidos/{id} - Reemplazar completamente un partido"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    data = request.get_json()
    required_fields = ['equipo_local', 'equipo_visitante', 'fecha', 'fase']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': f'Campo {field} requerido'}]}), 400
    
    try:
        fecha = datetime.fromisoformat(data['fecha'].replace('Z', '+00:00'))
    except:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'Formato de fecha inválido'}]}), 400
    
    partido.equipo_local = data['equipo_local']
    partido.equipo_visitante = data['equipo_visitante']
    partido.fecha = fecha
    partido.fase = data['fase']
    
    db.session.commit()
    return '', 204

@partidos_bp.route('/partidos/<int:id>', methods=['PATCH'])
def actualizar_parcial_partido(id):
    """PATCH /partidos/{id} - Actualizar parcialmente un partido"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    data = request.get_json()
    
    if 'equipo_local' in data:
        partido.equipo_local = data['equipo_local']
    if 'equipo_visitante' in data:
        partido.equipo_visitante = data['equipo_visitante']
    if 'fase' in data:
        partido.fase = data['fase']
    if 'fecha' in data:
        try:
            partido.fecha = datetime.fromisoformat(data['fecha'].replace('Z', '+00:00'))
        except:
            return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'Formato de fecha inválido'}]}), 400
    
    db.session.commit()
    return '', 204

@partidos_bp.route('/partidos/<int:id>', methods=['DELETE'])
def eliminar_partido(id):
    """DELETE /partidos/{id} - Eliminar partido"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    db.session.delete(partido)
    db.session.commit()
    return '', 204

@partidos_bp.route('/partidos/<int:id>/resultado', methods=['PUT'])
def actualizar_resultado(id):
    """PUT /partidos/{id}/resultado - Cargar o actualizar resultado"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    data = request.get_json()
    
    if 'local' not in data or 'visitante' not in data:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'Se requieren local y visitante'}]}), 400
    
    partido.goles_local = data['local']
    partido.goles_visitante = data['visitante']
    
    db.session.commit()
    return '', 204

# ==================== RUTAS DE USUARIOS ====================

@usuarios_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    """GET /usuarios - Listar usuarios con paginación"""
    limit = int(request.args.get('_limit', 10))
    offset = int(request.args.get('_offset', 0))
    
    total = Usuario.query.count()
    usuarios = Usuario.query.offset(offset).limit(limit).all()
    
    return jsonify({
        'usuarios': [u.to_resumen() for u in usuarios],
        '_links': generar_links('usuarios.listar_usuarios', total, limit, offset)
    }), 200

@usuarios_bp.route('/usuarios', methods=['POST'])
def crear_usuario():
    """POST /usuarios - Crear nuevo usuario"""
    data = request.get_json()
    
    if 'nombre' not in data or 'email' not in data:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'nombre y email requeridos'}]}), 400
    
    # Verificar email único
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'errors': [{'code': 'CONFLICT', 'message': 'Email ya registrado'}]}), 409
    
    usuario = Usuario(nombre=data['nombre'], email=data['email'])
    db.session.add(usuario)
    db.session.commit()
    
    return jsonify(usuario.to_dict()), 201

@usuarios_bp.route('/usuarios/<int:id>', methods=['GET'])
def obtener_usuario(id):
    """GET /usuarios/{id} - Obtener usuario por ID"""
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Usuario no encontrado'}]}), 404
    
    return jsonify(usuario.to_dict()), 200

@usuarios_bp.route('/usuarios/<int:id>', methods=['PUT'])
def reemplazar_usuario(id):
    """PUT /usuarios/{id} - Reemplazar usuario"""
    usuario = Usuario.query.get(id)
    data = request.get_json()
    
    if 'nombre' not in data or 'email' not in data:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'nombre y email requeridos'}]}), 400
    
    if not usuario:
        usuario = Usuario(id=id, nombre=data['nombre'], email=data['email'])
        db.session.add(usuario)
    else:
        # Verificar email único si cambió
        if usuario.email != data['email'] and Usuario.query.filter_by(email=data['email']).first():
            return jsonify({'errors': [{'code': 'CONFLICT', 'message': 'Email ya registrado'}]}), 409
        usuario.nombre = data['nombre']
        usuario.email = data['email']
    
    db.session.commit()
    return '', 204

@usuarios_bp.route('/usuarios/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    """DELETE /usuarios/{id} - Eliminar usuario"""
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Usuario no encontrado'}]}), 404
    
    db.session.delete(usuario)
    db.session.commit()
    return '', 204

# ==================== RUTAS DE PREDICCIONES ====================

@partidos_bp.route('/partidos/<int:id>/prediccion', methods=['POST'])
def crear_prediccion(id):
    """POST /partidos/{id}/prediccion - Registrar predicción"""
    partido = Partido.query.get(id)
    if not partido:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Partido no encontrado'}]}), 404
    
    data = request.get_json()
    
    if 'id_usuario' not in data or 'local' not in data or 'visitante' not in data:
        return jsonify({'errors': [{'code': 'BAD_REQUEST', 'message': 'Faltan campos requeridos'}]}), 400
    
    usuario = Usuario.query.get(data['id_usuario'])
    if not usuario:
        return jsonify({'errors': [{'code': 'NOT_FOUND', 'message': 'Usuario no encontrado'}]}), 404
    
    # Verificar que el partido no se haya jugado
    if partido.goles_local is not None and partido.goles_visitante is not None:
        return jsonify({'errors': [{'code': 'CONFLICT', 'message': 'El partido ya fue jugado'}]}), 409
    
    # Verificar predicción duplicada
    prediccion_existente = Prediccion.query.filter_by(
        id_usuario=data['id_usuario'],
        id_partido=id
    ).first()
    
    if prediccion_existente:
        return jsonify({'errors': [{'code': 'CONFLICT', 'message': 'Ya existe una predicción para este usuario y partido'}]}), 409
    
    prediccion = Prediccion(
        id_usuario=data['id_usuario'],
        id_partido=id,
        local=data['local'],
        visitante=data['visitante']
    )
    
    db.session.add(prediccion)
    db.session.commit()
    
    return '', 201

# ==================== RUTAS DE RANKING ====================

@ranking_bp.route('/ranking', methods=['GET'])
def obtener_ranking():
    """GET /ranking - Obtener ranking de usuarios"""
    limit = int(request.args.get('_limit', 10))
    offset = int(request.args.get('_offset', 0))
    
    usuarios = Usuario.query.all()
    ranking_items = []
    
    for usuario in usuarios:
        puntos = 0
        for prediccion in usuario.predicciones:
            if prediccion.partido.goles_local is not None:
                puntos += prediccion.calcular_puntos(prediccion.partido)
        
        ranking_items.append({
            'id_usuario': usuario.id,
            'puntos': puntos
        })
    
    # Ordenar por puntos descendente
    ranking_items.sort(key=lambda x: x['puntos'], reverse=True)
    
    # Paginación manual
    total = len(ranking_items)
    ranking_paginado = ranking_items[offset:offset + limit]
    
    return jsonify({
        'ranking': ranking_paginado,
        '_links': generar_links('ranking.obtener_ranking', total, limit, offset)
    }), 200