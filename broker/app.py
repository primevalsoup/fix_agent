"""
Broker Flask Application
Provides REST API and WebSocket interface for the broker dashboard
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import csv
import uuid
from datetime import datetime
from models import (
    init_db, get_session, Order, Execution, Stock,
    OrderStatus, OrderSide, OrderType, TimeInForce
)
from fix_server import FIXServer
import threading

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_db('broker.db')

# Start FIX server
fix_server = FIXServer(host='0.0.0.0', port=5001)


def order_received_callback(order_id):
    """Callback when new order is received via FIX"""
    # Notify dashboard via WebSocket
    socketio.emit('order_update', {'order_id': order_id})


fix_server.set_order_callback(order_received_callback)
fix_server.start()


# ============= Stock Universe API =============

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """Get all stocks from the universe"""
    session = get_session()
    stocks = session.query(Stock).all()
    session.close()

    return jsonify([{
        'id': s.id,
        'symbol': s.symbol,
        'last_price': s.last_price,
        'updated_at': s.updated_at.isoformat()
    } for s in stocks])


@app.route('/api/stocks/reload', methods=['POST'])
def reload_stocks():
    """Reload stock universe from CSV file"""
    try:
        session = get_session()

        # Clear existing stocks
        session.query(Stock).delete()

        # Load from CSV
        with open('stock_universe.csv', 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                stock = Stock(
                    symbol=row['symbol'],
                    last_price=float(row['last_price'])
                )
                session.add(stock)
                count += 1

        session.commit()
        session.close()

        # Notify dashboard
        socketio.emit('stocks_reloaded', {'count': count})

        return jsonify({'success': True, 'count': count})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============= Orders API =============

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    session = get_session()
    orders = session.query(Order).order_by(Order.created_at.desc()).all()

    result = []
    for o in orders:
        result.append({
            'id': o.id,
            'cl_ord_id': o.cl_ord_id,
            'sender_comp_id': o.sender_comp_id,
            'symbol': o.symbol,
            'side': o.side.value,
            'order_type': o.order_type.value,
            'quantity': o.quantity,
            'limit_price': o.limit_price,
            'time_in_force': o.time_in_force.value,
            'status': o.status.value,
            'filled_quantity': o.filled_quantity,
            'remaining_quantity': o.remaining_quantity,
            'reject_reason': o.reject_reason,
            'created_at': o.created_at.isoformat(),
            'updated_at': o.updated_at.isoformat()
        })

    session.close()
    return jsonify(result)


@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Get a specific order with executions"""
    session = get_session()
    order = session.query(Order).filter_by(id=order_id).first()

    if not order:
        session.close()
        return jsonify({'error': 'Order not found'}), 404

    executions = [{
        'id': e.id,
        'exec_id': e.exec_id,
        'exec_quantity': e.exec_quantity,
        'exec_price': e.exec_price,
        'executed_at': e.executed_at.isoformat()
    } for e in order.executions]

    result = {
        'id': order.id,
        'cl_ord_id': order.cl_ord_id,
        'sender_comp_id': order.sender_comp_id,
        'symbol': order.symbol,
        'side': order.side.value,
        'order_type': order.order_type.value,
        'quantity': order.quantity,
        'limit_price': order.limit_price,
        'time_in_force': order.time_in_force.value,
        'status': order.status.value,
        'filled_quantity': order.filled_quantity,
        'remaining_quantity': order.remaining_quantity,
        'reject_reason': order.reject_reason,
        'created_at': order.created_at.isoformat(),
        'executions': executions
    }

    session.close()
    return jsonify(result)


@app.route('/api/orders/<int:order_id>/execute', methods=['POST'])
def execute_order(order_id):
    """Execute an order (fully or partially)"""
    try:
        data = request.json
        exec_quantity = data.get('quantity')  # If None, execute fully

        session = get_session()
        order = session.query(Order).filter_by(id=order_id).first()

        if not order:
            session.close()
            return jsonify({'error': 'Order not found'}), 404

        if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
            session.close()
            return jsonify({'error': 'Order cannot be executed'}), 400

        # Get stock price
        stock = session.query(Stock).filter_by(symbol=order.symbol).first()
        if not stock:
            session.close()
            return jsonify({'error': 'Stock not found in universe'}), 400

        exec_price = stock.last_price

        # Validate limit price
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and order.limit_price < exec_price:
                session.close()
                return jsonify({'error': 'Buy limit price too low'}), 400
            if order.side == OrderSide.SELL and order.limit_price > exec_price:
                session.close()
                return jsonify({'error': 'Sell limit price too high'}), 400

        # Determine execution quantity
        if exec_quantity is None:
            exec_quantity = order.remaining_quantity
        else:
            exec_quantity = min(exec_quantity, order.remaining_quantity)

        # Handle Time in Force
        if order.time_in_force == TimeInForce.FOK:
            # Fill or Kill - must execute fully
            if exec_quantity != order.remaining_quantity:
                session.close()
                return jsonify({'error': 'FOK order must be filled completely'}), 400

        if order.time_in_force == TimeInForce.IOC:
            # Immediate or Cancel - execute what we can, cancel the rest
            pass

        # Create execution
        execution = Execution(
            order_id=order.id,
            exec_id=str(uuid.uuid4())[:8],
            exec_quantity=exec_quantity,
            exec_price=exec_price
        )
        session.add(execution)

        # Update order
        order.filled_quantity += exec_quantity
        order.remaining_quantity -= exec_quantity

        if order.remaining_quantity == 0:
            order.status = OrderStatus.FILLED
            exec_type = '2'  # Fill
            ord_status = '2'  # Filled
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
            exec_type = '1'  # PartialFill
            ord_status = '1'  # PartiallyFilled

        session.commit()

        # Calculate average price
        total_value = sum(e.exec_quantity * e.exec_price for e in order.executions)
        avg_px = total_value / order.filled_quantity if order.filled_quantity > 0 else 0

        # Send execution report via FIX
        fix_server.send_execution_to_client(
            cl_ord_id=order.cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type=exec_type,
            ord_status=ord_status,
            last_qty=exec_quantity,
            last_px=exec_price,
            cum_qty=order.filled_quantity,
            avg_px=avg_px,
            symbol=order.symbol,
            side='1' if order.side == OrderSide.BUY else '2',
            order_qty=order.quantity,
            ord_type='1' if order.order_type == OrderType.MARKET else '2'
        )

        session.close()

        # Notify dashboard
        socketio.emit('order_update', {'order_id': order_id})

        return jsonify({'success': True, 'execution_id': execution.exec_id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Cancel an order"""
    try:
        session = get_session()
        order = session.query(Order).filter_by(id=order_id).first()

        if not order:
            session.close()
            return jsonify({'error': 'Order not found'}), 404

        if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
            session.close()
            return jsonify({'error': 'Order cannot be canceled'}), 400

        order.status = OrderStatus.CANCELED
        session.commit()

        # Send execution report via FIX
        fix_server.send_execution_to_client(
            cl_ord_id=order.cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='4',  # Canceled
            ord_status='4',  # Canceled
            cum_qty=order.filled_quantity,
            avg_px=0,
            symbol=order.symbol,
            side='1' if order.side == OrderSide.BUY else '2',
            order_qty=order.quantity,
            ord_type='1' if order.order_type == OrderType.MARKET else '2'
        )

        session.close()

        # Notify dashboard
        socketio.emit('order_update', {'order_id': order_id})

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders/<int:order_id>/reject', methods=['POST'])
def reject_order(order_id):
    """Reject an order"""
    try:
        data = request.json
        reason = data.get('reason', 'Rejected by admin')

        session = get_session()
        order = session.query(Order).filter_by(id=order_id).first()

        if not order:
            session.close()
            return jsonify({'error': 'Order not found'}), 404

        if order.status != OrderStatus.NEW:
            session.close()
            return jsonify({'error': 'Only new orders can be rejected'}), 400

        order.status = OrderStatus.REJECTED
        order.reject_reason = reason
        session.commit()

        # Send execution report via FIX
        fix_server.send_execution_to_client(
            cl_ord_id=order.cl_ord_id,
            sender_comp_id=order.sender_comp_id,
            exec_type='8',  # Rejected
            ord_status='8',  # Rejected
            cum_qty=0,
            avg_px=0,
            symbol=order.symbol,
            side='1' if order.side == OrderSide.BUY else '2',
            order_qty=order.quantity,
            ord_type='1' if order.order_type == OrderType.MARKET else '2'
        )

        session.close()

        # Notify dashboard
        socketio.emit('order_update', {'order_id': order_id})

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= WebSocket Events =============

@socketio.on('connect')
def handle_connect():
    """Client connected to WebSocket"""
    print('[WebSocket] Client connected')
    emit('connected', {'data': 'Connected to broker'})


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected from WebSocket"""
    print('[WebSocket] Client disconnected')


# ============= Main =============

if __name__ == '__main__':
    # Load initial stock universe
    try:
        session = get_session()
        if session.query(Stock).count() == 0:
            with open('stock_universe.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stock = Stock(
                        symbol=row['symbol'],
                        last_price=float(row['last_price'])
                    )
                    session.add(stock)
            session.commit()
            print('[Broker] Loaded stock universe')
        session.close()
    except Exception as e:
        print(f'[Broker] Error loading stock universe: {e}')

    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
