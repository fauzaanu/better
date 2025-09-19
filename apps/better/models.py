from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


# Create your models here.

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class ScoreDay(BaseModel):
    day = models.DateField()
    score = models.PositiveIntegerField(null=True)
    max_score = models.PositiveIntegerField(null=True)



class TargetCategory(BaseModel):
    day = models.ForeignKey(ScoreDay, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    score = models.PositiveIntegerField(null=True)
    max_score = models.PositiveIntegerField(null=True)


    def __str__(self):
        return self.name

    def get_score(self):
        # TODO: this is a placeholder
        return 1


class Importance(models.Model):
    label = models.CharField(max_length=200)
    score = models.PositiveIntegerField()

    # IMPORTANCE_IMPORTANT = 1
    #     IMPORTANCE_LIFECHANGING = 2
    #     IMPORTANCE_CRITICAL = 6
    #
    #     IMPORTANCE_CHOICES = (
    #         ('Important', IMPORTANCE_IMPORTANT),
    #         ('Life-changing', IMPORTANCE_LIFECHANGING),
    #         ('Critical', IMPORTANCE_CRITICAL),
    #     )


class Target(BaseModel):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(TargetCategory, on_delete=models.CASCADE)
    importance = models.ForeignKey(Importance, on_delete=models.CASCADE)
    is_achieved = models.BooleanField(default=False)
