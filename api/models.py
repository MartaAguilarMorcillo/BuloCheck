import uuid
from django.db import models


class AnonymousUser(models.Model):
    """
    Usuario anónimo identificado por un UUID generado en el navegador.
    No requiere registro ni contraseña.
    El UUID se genera en la extensión y se guarda en localStorage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "anonymous_users"

    def __str__(self):
        return str(self.id)


class NewsCheck(models.Model):
    """
    Cada vez que un usuario analiza una noticia se guarda un registro aquí.
    """
    LABEL_CHOICES = [
        ("REAL", "Real"),
        ("FAKE", "Fake"),
    ]

    user = models.ForeignKey(
        AnonymousUser,
        on_delete=models.CASCADE,
        related_name="checks",
    )
    title = models.TextField()
    text = models.TextField()
    # Fuente opcional: la URL o nombre del medio que el usuario indica
    source = models.CharField(max_length=500, blank=True, null=True)
    label = models.CharField(max_length=4, choices=LABEL_CHOICES)
    # Confianza del modelo: valor entre 0 y 1
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "news_checks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.confidence:.0%}) — {self.title[:60]}"
