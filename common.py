from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from utils import encode_id
from asgiref.sync import sync_to_async


class AliasModel(models.Model):
    alias_id = models.CharField(max_length=10, blank=True, null=True)
    # alias_id = models.CharField(max_length=10, unique=True, editable=False, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.alias_id:
            if self.id:
                self.alias_id = encode_id(self.id)
        super(AliasModel, self).save(*args, **kwargs)

    @property
    async def async_alias(self):
        if self.alias_id:
            return self.alias_id
        self.alias_id = encode_id(self.id)
        await sync_to_async(self.save)(update_fields=['alias_id'])
        return self.alias_id
    
    @property
    def alias(self):
        if self.alias_id:
            return self.alias_id
        self.alias_id = encode_id(self.id)
        self.save(update_fields=['alias_id'])
        return self.alias_id

@receiver(post_save, sender=AliasModel)
def set_alias_id(sender, instance, created, **kwargs):
    if created:
        instance.alias_id = encode_id(instance.id)
        instance.save(update_fields=['alias_id'])