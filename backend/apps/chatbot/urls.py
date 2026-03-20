from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("conversations/start/", views.StartConversationView.as_view(), name="start"),
    path("conversations/", views.ConversationListView.as_view(), name="list"),
    path("conversations/<int:pk>/", views.ConversationDetailView.as_view(), name="detail"),
    path("conversations/<int:conversation_id>/messages/", views.SendMessageView.as_view(), name="send-message"),
    path("conversations/<int:conversation_id>/history/", views.MessageHistoryView.as_view(), name="message-history"),
    path("webhooks/whatsapp/", views.WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
