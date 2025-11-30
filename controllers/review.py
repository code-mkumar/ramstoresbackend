from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Review, Product, User, Order, OrderItem,Notification
from datetime import datetime, timedelta

review_bp = Blueprint("review", __name__)


# ------------------------------------------------------------
# GET ALL REVIEWS FOR A PRODUCT (ONLY APPROVED)
# ------------------------------------------------------------
@review_bp.route("/products/<int:product_id>/reviews", methods=["GET"])
def get_product_reviews(product_id):
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        reviews = Review.query.filter_by(
            product_id=product_id,
            is_approved=True
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            "success": True,
            "reviews": [{
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "user_name": r.user.full_name,
                "created_at": r.created_at.isoformat()
            } for r in reviews.items],
            "pagination": {
                "page": reviews.page,
                "per_page": reviews.per_page,
                "total": reviews.total,
                "pages": reviews.pages
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# CREATE A NEW REVIEW (ONLY BUYERS & ADMINS)
# ------------------------------------------------------------
@review_bp.route("/products/<int:product_id>/review", methods=["POST"])
@jwt_required()
def submit_review(product_id):
    try:
        user_id = get_jwt_identity()

        # Parse data
        data = request.get_json()
        rating = data.get("rating")
        comment = data.get("comment", "")

        # Validate rating
        if not rating or rating < 1 or rating > 5:
            return jsonify({"success": False, "message": "Rating must be between 1 and 5"}), 400

        # Check product exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404

        # Check user already reviewed this product
        existing_review = Review.query.filter_by(user_id=user_id, product_id=product_id).first()
        if existing_review:
            return jsonify({"success": False, "message": "You have already reviewed this product"}), 400

        # Verify purchase using Order + OrderItem
        purchased = (
            db.session.query(OrderItem)
            .join(Order)
            .filter(
                OrderItem.product_id == product_id,
                Order.user_id == user_id,
                Order.status == "Delivered"
            )
            .first()
        )

        if not purchased:
            return jsonify({
                "success": False,
                "message": "You can review only after the product is delivered"
            }), 403

        # Create review
        review = Review(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            comment=comment,
            is_approved=False,         # user reviews require admin approval
            created_at=datetime.utcnow()+timedelta(hours=5, minutes=30)
        )

        db.session.add(review)
        db.session.commit()

        # Create notification
        notification = Notification(
            user_id=user_id,
            title="Thank you for your review!",
            message=f"Thanks for reviewing the product '{product.name}'.",
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Review submitted successfully! Awaiting approval.",
            "notification": "Thank you message sent."
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
# ------------------------------------------------------------
# UPDATE REVIEW (OWNER OR ADMIN)
# ------------------------------------------------------------
@review_bp.route("/reviews/<int:review_id>", methods=["PUT"])
@jwt_required()
def update_review(review_id):
    try:
        current_user_id = get_jwt_identity()
        review = Review.query.get_or_404(review_id)
        user = User.query.get(current_user_id)

        if review.user_id != current_user_id and user.role != "admin":
            return jsonify({"success": False, "message": "Access denied"}), 403

        data = request.get_json()

        if "rating" in data:
            if not (1 <= data["rating"] <= 5):
                return jsonify({"success": False, "message": "Invalid rating"}), 400
            review.rating = data["rating"]

        if "comment" in data:
            review.comment = data["comment"]

        review.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Review updated",
            "review": {
                "id": review.id,
                "rating": review.rating,
                "comment": review.comment
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# DELETE REVIEW (OWNER OR ADMIN)
# ------------------------------------------------------------
@review_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    try:
        current_user_id = get_jwt_identity()
        review = Review.query.get_or_404(review_id)
        user = User.query.get(current_user_id)

        if review.user_id != current_user_id and user.role != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        db.session.delete(review)
        db.session.commit()

        return jsonify({"success": True, "message": "Review deleted"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# APPROVE / DISAPPROVE REVIEW (ADMIN ONLY)
# ------------------------------------------------------------
@review_bp.route("/reviews/<int:review_id>/approve", methods=["POST"])
@jwt_required()
def approve_review(review_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        review = Review.query.get_or_404(review_id)
        data = request.get_json()

        review.is_approved = data.get("approve", True)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Review {'approved' if review.is_approved else 'disapproved'}"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# GET PENDING REVIEWS (ADMIN ONLY)
# ------------------------------------------------------------
@review_bp.route("/admin/reviews/pending", methods=["GET"])
@jwt_required()
def get_pending_reviews():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        reviews = Review.query.filter_by(is_approved=False).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            "success": True,
            "reviews": [{
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "user_name": r.user.full_name,
                "product_name": r.product.name,
                "created_at": r.created_at.isoformat()
            } for r in reviews.items],
            "pagination": {
                "page": reviews.page,
                "per_page": reviews.per_page,
                "total": reviews.total,
                "pages": reviews.pages
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
