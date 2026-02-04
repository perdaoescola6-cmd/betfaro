from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlmodel import Session, select
from datetime import datetime, timedelta
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path="../.env")

from database import create_db_and_tables, get_session
from models import User, Subscription, ChatMessage, AuditLog
from schemas import UserCreate, UserLogin, UserResponse, Token, ChatMessageRequest, ChatResponse, AdminGrantRequest, AdminRevokeRequest, SubscriptionResponse
from auth import get_current_user, get_admin_user, verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from chatbot import ChatBot
from picks_engine import picks_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BetFaro API", version="1.0.0")

# CORS middleware - Production configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Key", "X-Admin-Key"],
)

# Initialize chatbot
chatbot = ChatBot()

# Environment variables
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
PLUS_URL = os.getenv("PLUS_URL")
PRO_URL = os.getenv("PRO_URL")
ELITE_URL = os.getenv("ELITE_URL")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

# Utility functions
def check_admin_api_key(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key"
        )
    return True

def check_user_subscription(user: User) -> bool:
    """Check if user has active subscription"""
    session = next(get_session())
    subscription = session.exec(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.utcnow()
        )
    ).first()
    return subscription is not None

# Auth endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, session: Session = Depends(get_session)):
    """Register new user"""
    # Check if user already exists
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        created_at=datetime.utcnow()
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Log registration
    audit = AuditLog(
        user_id=user.id,
        action="user_registered",
        details={"email": user.email}
    )
    session.add(audit)
    session.commit()
    
    logger.info(f"User registered: {user.email}")
    return user

@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, session: Session = Depends(get_session)):
    """Login user and return JWT token"""
    user = session.exec(select(User).where(User.email == user_data.email)).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Log login
    audit = AuditLog(
        user_id=user.id,
        action="user_login",
        details={"email": user.email}
    )
    session.add(audit)
    session.commit()
    
    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Get current user info with subscription"""
    # Get active subscription
    subscription = session.exec(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.utcnow()
        ).order_by(Subscription.created_at.desc())
    ).first()
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "is_active": current_user.is_active,
        "subscription": {
            "plan": subscription.plan,
            "status": subscription.status,
            "expires_at": subscription.expires_at
        } if subscription else None
    }

@app.get("/api/auth/subscription")
async def get_subscription_status(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Get user subscription status"""
    subscription = session.exec(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        ).order_by(Subscription.created_at.desc())
    ).first()
    
    if not subscription:
        return {
            "has_subscription": False,
            "plan": None,
            "expires_at": None,
            "status": "none"
        }
    
    return {
        "has_subscription": True,
        "plan": subscription.plan,
        "expires_at": subscription.expires_at,
        "status": subscription.status
    }

# Chat endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessageRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Process chat message"""
    # Check subscription
    if not check_user_subscription(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to use chat"
        )
    
    # Save user message
    user_message = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=message.content,
        extra_data=None,
        created_at=datetime.utcnow()
    )
    session.add(user_message)
    
    # Process message
    try:
        response = await chatbot.process_message(message.content, current_user)
        
        # Save bot response
        bot_message = ChatMessage(
            user_id=current_user.id,
            role="assistant",
            content=response,
            extra_data=None,
            created_at=datetime.utcnow()
        )
        session.add(bot_message)
        session.commit()
        
        logger.info(f"Chat processed for user {current_user.email}")
        
        return ChatResponse(
            response=response,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Chat processing error: {str(e)}\n{error_trace}")
        
        # Return friendly error message instead of generic error
        error_response = "⚠️ A API está instável agora. Tente novamente em alguns segundos.\n\n"
        error_response += "Se o problema persistir, verifique:\n"
        error_response += "  • Se os nomes dos times estão corretos\n"
        error_response += "  • Use o formato: Time A x Time B\n\n"
        error_response += "💡 Exemplos: Arsenal x Chelsea, Benfica vs Porto"
        
        return ChatResponse(
            response=error_response,
            timestamp=datetime.utcnow()
        )

@app.get("/api/chat/history")
async def get_chat_history(current_user: User = Depends(get_current_user), session: Session = Depends(get_session), limit: int = 50):
    """Get chat history"""
    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.user_id == current_user.id
        ).order_by(ChatMessage.created_at.desc()).limit(limit)
    ).all()
    
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.created_at
        }
        for msg in reversed(messages)
    ]

# Plans/Billing endpoints
@app.get("/api/plans")
async def get_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "id": "plus",
                "name": "Plus",
                "price": "R$30/mês",
                "features": [
                    "Acesso ao chatbot",
                    "Análises de times",
                    "Análises de jogos",
                    "Estatísticas básicas"
                ],
                "url": PLUS_URL
            },
            {
                "id": "pro",
                "name": "Pro", 
                "price": "R$60/mês",
                "features": [
                    "Todos os recursos Plus",
                    "Estatísticas avançadas",
                    "Mais históricos",
                    "Análises detalhadas"
                ],
                "url": PRO_URL
            },
            {
                "id": "elite",
                "name": "Elite",
                "price": "R$100/mês", 
                "features": [
                    "Todos os recursos Pro",
                    "Scanner de odds (em breve)",
                    "Análises premium",
                    "Suporte prioritário"
                ],
                "url": ELITE_URL
            }
        ]
    }

# Admin endpoints
@app.post("/api/admin/grant")
async def grant_subscription(
    request: AdminGrantRequest,
    session: Session = Depends(get_session),
    _: bool = Depends(check_admin_api_key)
):
    """Grant subscription to user"""
    # Find user
    user = session.exec(select(User).where(User.email == request.email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create or update subscription
    expires_at = datetime.utcnow() + timedelta(days=request.days)
    
    # Cancel existing subscriptions
    existing = session.exec(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        )
    ).all()
    
    for sub in existing:
        sub.status = "cancelled"
    
    # Create new subscription
    subscription = Subscription(
        user_id=user.id,
        plan=request.plan,
        status="active",
        expires_at=expires_at,
        updated_at=datetime.utcnow()
    )
    
    session.add(subscription)
    
    # Log action
    audit = AuditLog(
        user_id=user.id,
        action="subscription_granted",
        details={
            "plan": request.plan,
            "days": request.days,
            "expires_at": expires_at.isoformat()
        }
    )
    session.add(audit)
    session.commit()
    
    logger.info(f"Subscription granted to {user.email}: {request.plan}")
    
    return {"message": f"Subscription {request.plan} granted to {user.email}"}

@app.post("/api/admin/revoke")
async def revoke_subscription(
    request: AdminRevokeRequest,
    session: Session = Depends(get_session),
    _: bool = Depends(check_admin_api_key)
):
    """Revoke user subscription"""
    # Find user
    user = session.exec(select(User).where(User.email == request.email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cancel active subscriptions
    subscriptions = session.exec(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        )
    ).all()
    
    if not subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    for sub in subscriptions:
        sub.status = "cancelled"
        sub.updated_at = datetime.utcnow()
    
    # Log action
    audit = AuditLog(
        user_id=user.id,
        action="subscription_revoked",
        details={"email": request.email}
    )
    session.add(audit)
    session.commit()
    
    logger.info(f"Subscription revoked for {user.email}")
    
    return {"message": f"Subscription revoked for {request.email}"}

@app.get("/api/admin/users")
async def list_users(
    search: str = None,
    session: Session = Depends(get_session),
    _: bool = Depends(check_admin_api_key)
):
    """List users with optional search"""
    query = select(User)
    if search:
        query = query.where(User.email.contains(search))
    
    users = session.exec(query.order_by(User.created_at.desc())).all()
    
    result = []
    for user in users:
        subscription = session.exec(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == "active"
            ).order_by(Subscription.created_at.desc())
        ).first()
        
        result.append({
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
            "is_active": user.is_active,
            "subscription": {
                "plan": subscription.plan,
                "expires_at": subscription.expires_at,
                "status": subscription.status
            } if subscription else None
        })
    
    return result

@app.get("/api/admin/user/{email}")
async def get_user_details(
    email: str,
    session: Session = Depends(get_session),
    _: bool = Depends(check_admin_api_key)
):
    """Get detailed user information"""
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    subscriptions = session.exec(
        select(Subscription).where(
            Subscription.user_id == user.id
        ).order_by(Subscription.created_at.desc())
    ).all()
    
    chat_messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.user_id == user.id
        ).order_by(ChatMessage.created_at.desc()).limit(20)
    ).all()
    
    audit_logs = session.exec(
        select(AuditLog).where(
            AuditLog.user_id == user.id
        ).order_by(AuditLog.created_at.desc()).limit(10)
    ).all()
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
            "is_active": user.is_active
        },
        "subscriptions": [
            {
                "id": sub.id,
                "plan": sub.plan,
                "status": sub.status,
                "expires_at": sub.expires_at,
                "created_at": sub.created_at
            }
            for sub in subscriptions
        ],
        "recent_chats": [
            {
                "role": msg.role,
                "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                "created_at": msg.created_at
            }
            for msg in chat_messages
        ],
        "audit_logs": [
            {
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in audit_logs
        ]
    }

@app.patch("/api/admin/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: int,
    plan: str = None,
    status: str = None,
    days: int = None,
    session: Session = Depends(get_session),
    _: bool = Depends(check_admin_api_key)
):
    """Update user subscription - Admin only"""
    # Find user
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate plan
    valid_plans = ["free", "plus", "pro", "elite"]
    if plan and plan.lower() not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}"
        )
    
    # Handle "free" plan - cancel subscription
    if plan and plan.lower() == "free":
        existing = session.exec(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == "active"
            )
        ).all()
        
        for sub in existing:
            sub.status = "cancelled"
            sub.updated_at = datetime.utcnow()
        
        # Log action
        audit = AuditLog(
            user_id=user.id,
            action="subscription_cancelled_by_admin",
            details={"previous_plan": existing[0].plan if existing else None}
        )
        session.add(audit)
        session.commit()
        
        return {
            "id": user.id,
            "email": user.email,
            "subscription": None,
            "message": "Subscription cancelled"
        }
    
    # Get or create subscription
    subscription = session.exec(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        )
    ).first()
    
    if subscription:
        # Update existing
        old_plan = subscription.plan
        if plan:
            subscription.plan = plan.lower()
        if status:
            subscription.status = status
        if days:
            subscription.expires_at = datetime.utcnow() + timedelta(days=days)
        subscription.updated_at = datetime.utcnow()
    else:
        # Create new subscription
        old_plan = None
        subscription = Subscription(
            user_id=user.id,
            plan=plan.lower() if plan else "plus",
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=days or 30),
            updated_at=datetime.utcnow()
        )
        session.add(subscription)
    
    # Log action
    audit = AuditLog(
        user_id=user.id,
        action="subscription_updated_by_admin",
        details={
            "old_plan": old_plan,
            "new_plan": subscription.plan,
            "expires_at": subscription.expires_at.isoformat(),
            "provider": "manual"
        }
    )
    session.add(audit)
    session.commit()
    session.refresh(subscription)
    
    logger.info(f"Subscription updated for {user.email}: {subscription.plan}")
    
    return {
        "id": user.id,
        "email": user.email,
        "subscription": {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "expires_at": subscription.expires_at,
            "provider": "manual"
        },
        "message": "Subscription updated successfully"
    }

# Picks endpoints (Elite only)
@app.get("/api/picks")
async def get_picks(
    range: str = "both",
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get daily picks - Elite only feature"""
    # Check subscription
    subscription = session.exec(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.utcnow()
        )
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required"
        )
    
    # Check if Elite plan
    if subscription.plan.lower() != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Picks Diários é exclusivo do plano Elite. Faça upgrade para receber as melhores oportunidades automaticamente."
        )
    
    # Validate range parameter
    if range not in ["today", "tomorrow", "both"]:
        range = "both"
    
    try:
        result = await picks_engine.get_daily_picks(range_type=range, force_refresh=refresh)
        logger.info(f"Picks generated for user {current_user.email}: {len(result.get('picks', []))} picks")
        return result
    except Exception as e:
        logger.error(f"Error generating picks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não consegui atualizar os picks agora. Tente novamente em instantes."
        )

# Internal chat endpoint (for Next.js API - auth handled by Next.js)
@app.post("/api/internal/chat")
async def chat_internal(
    message: ChatMessageRequest,
    x_internal_key: str = Header(None),
    x_user_id: str = Header(None),
    x_user_email: str = Header(None),
    session: Session = Depends(get_session)
):
    """Internal endpoint for chat - called by Next.js API after auth verification"""
    internal_key = os.getenv("INTERNAL_API_KEY", "betfaro_internal_2024")
    if x_internal_key != internal_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal key"
        )
    
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID required"
        )
    
    # Get user from database or create if not exists (sync from Supabase)
    user = session.exec(select(User).where(User.id == x_user_id)).first()
    if not user:
        # Auto-create user from Supabase auth
        user = User(
            id=x_user_id,
            email=x_user_email or "unknown@betfaro.com",
            hashed_password="supabase_auth",  # Not used, auth is via Supabase
            is_active=True,
            is_admin=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Auto-created user from Supabase: {x_user_email}")
    
    # Check subscription
    if not check_user_subscription(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to use chat"
        )
    
    # Save user message
    user_message = ChatMessage(
        user_id=user.id,
        role="user",
        content=message.content,
        extra_data=None,
        created_at=datetime.utcnow()
    )
    session.add(user_message)
    
    # Process message
    try:
        response = await chatbot.process_message(message.content, user)
        
        # Save bot response
        bot_message = ChatMessage(
            user_id=user.id,
            role="assistant",
            content=response,
            extra_data=None,
            created_at=datetime.utcnow()
        )
        session.add(bot_message)
        session.commit()
        
        logger.info(f"Internal chat processed for user {user.email}")
        
        return ChatResponse(
            response=response,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Internal chat processing error: {str(e)}\n{error_trace}")
        
        error_response = "⚠️ A API está instável agora. Tente novamente em alguns segundos.\n\n"
        error_response += "Se o problema persistir, verifique:\n"
        error_response += "  • Se os nomes dos times estão corretos\n"
        error_response += "  • Use o formato: Time A x Time B\n\n"
        error_response += "💡 Exemplos: Arsenal x Chelsea, Benfica vs Porto"
        
        return ChatResponse(
            response=error_response,
            timestamp=datetime.utcnow()
        )

# Internal picks endpoint (for Next.js API - no auth required, auth handled by Next.js)
@app.get("/api/internal/picks")
async def get_picks_internal(
    range: str = "both",
    refresh: bool = False,
    x_internal_key: str = Header(None)
):
    """Internal endpoint for picks - called by Next.js API after auth verification"""
    # Simple internal key check
    internal_key = os.getenv("INTERNAL_API_KEY", "betfaro_internal_2024")
    if x_internal_key != internal_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal key"
        )
    
    # Validate range parameter
    if range not in ["today", "tomorrow", "both"]:
        range = "both"
    
    try:
        result = await picks_engine.get_daily_picks(range_type=range, force_refresh=refresh)
        logger.info(f"Internal picks generated: {len(result.get('picks', []))} picks")
        return result
    except Exception as e:
        logger.error(f"Error generating picks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não consegui atualizar os picks agora. Tente novamente em instantes."
        )

# Health check
@app.get("/api/health")
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
