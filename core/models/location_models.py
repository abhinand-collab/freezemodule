from django.db import models

class Region(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class City(models.Model):
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="cities"
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("region", "name")

    def __str__(self):
        return f"{self.name} - {self.region.name}"

class Club(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="clubs"
    )
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("city", "name")

    def __str__(self):
        return f"{self.name} - {self.city.name}"
